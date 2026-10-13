param(
    [ValidateSet('FD001','FD002','FD003','FD004')][string]$Dataset = 'FD001',
    [ValidateSet('train','test')][string]$Split = 'train',
    [int[]]$Sizes = @(500, 5000, 20000),
    [ValidateRange(1,1000000)][int]$MaxOffsetsPerTrigger = 200
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$KafkaCompose = Join-Path $Root 'docker\kafka\compose.yaml'
$Producer = Join-Path $Root 'scripts\kafka\cmapss_producer.py'
$SparkRunner = Join-Path $Root 'scripts\phase3\run_spark_phase3.ps1'
$ResultsDir = Join-Path $Root 'results\phase7'
$Phase3ResultsDir = Join-Path $Root 'results\phase3'
$DocsDir = Join-Path $Root 'docs\project'
$RunId = Get-Date -Format 'yyyyMMddHHmmss'
$Docker = (Get-Command docker.exe -ErrorAction Stop).Source

foreach ($p in @($Python, $KafkaCompose, $Producer, $SparkRunner)) {
    if (-not (Test-Path $p)) { throw "Required project file missing: $p" }
}
$InvalidSizes = @($Sizes | Where-Object { $_ -lt 1 })
if ($Sizes.Count -lt 1 -or $InvalidSizes.Count -gt 0) {
    throw 'Supply at least one positive size, e.g. -Sizes 500 or -Sizes 500,5000,20000.'
}
New-Item -ItemType Directory -Force -Path $ResultsDir, $Phase3ResultsDir, $DocsDir | Out-Null

# Confirm the Phase 2 Kafka service responds over the Docker network.
& $Docker compose -f $KafkaCompose exec -T kafka kafka-topics.sh --bootstrap-server kafka:9093 --list *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Kafka is not responding. Start Phase 2 first with .\scripts\kafka\start_kafka.ps1.'
}

$Rows = @()
foreach ($Size in $Sizes) {
    $ShortDataset = $Dataset.ToLowerInvariant()
    $Topic = "dare-rul-p7-$ShortDataset-$Split-$Size-$RunId"
    $RunLabel = "p7_${Dataset}_${Split}_${Size}_${RunId}"
    $ProducerLog = Join-Path $ResultsDir "${RunLabel}_producer.log"
    $SparkLog = Join-Path $ResultsDir "${RunLabel}_spark.log"
    $SummaryPath = Join-Path $Phase3ResultsDir "${RunLabel}_summary.json"

    Write-Host "`n=== Phase 7 stream replay/drain test: $Size messages ===" -ForegroundColor Cyan
    Write-Host "Topic: $Topic"
    Write-Host "Run label: $RunLabel"

    & $Docker compose -f $KafkaCompose exec -T kafka kafka-topics.sh --bootstrap-server kafka:9093 --create --topic $Topic --partitions 4 --replication-factor 1
    if ($LASTEXITCODE -ne 0) { throw "Could not create unique Kafka topic $Topic" }
    Start-Sleep -Seconds 2

    $ProducerOutput = & $Python $Producer --dataset $Dataset --split $Split --topic $Topic --max-messages $Size --rate 0 --bootstrap-servers 'localhost:9092' 2>&1 | Tee-Object -FilePath $ProducerLog
    $ProducerExit = $LASTEXITCODE
    $ProducerText = ($ProducerOutput | ForEach-Object { [string]$_ }) -join "`n"
    if ($ProducerExit -ne 0) { throw "Producer failed for $Size messages. See $ProducerLog" }
    $DeliveredMatch = [regex]::Match($ProducerText, 'Delivered:\s*(\d+);\s*failed:\s*(\d+);\s*outstanding after flush:\s*(\d+)')
    $ProducerElapsedMatch = [regex]::Match($ProducerText, 'Elapsed seconds:\s*([\d.]+)')
    $ProducerRateMatch = [regex]::Match($ProducerText, 'achieved delivery rate:\s*([\d.]+)\s*messages/sec')
    if (-not $DeliveredMatch.Success -or -not $ProducerElapsedMatch.Success) {
        throw "Could not parse producer summary. See $ProducerLog"
    }
    $Delivered = [int]$DeliveredMatch.Groups[1].Value
    $Failed = [int]$DeliveredMatch.Groups[2].Value
    $Outstanding = [int]$DeliveredMatch.Groups[3].Value
    $ProducerSeconds = [double]::Parse($ProducerElapsedMatch.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
    $ProducerRate = if ($ProducerRateMatch.Success) { [double]::Parse($ProducerRateMatch.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture) } else { 0.0 }
    if ($Delivered -ne $Size -or $Failed -ne 0 -or $Outstanding -ne 0) {
        throw "Producer delivery mismatch for $Size messages: delivered=$Delivered failed=$Failed outstanding=$Outstanding. See $ProducerLog"
    }

    $SparkOutput = & $SparkRunner -Topic $Topic -RunLabel $RunLabel -ExpectedMessages $Size -MaxOffsetsPerTrigger $MaxOffsetsPerTrigger 2>&1 | Tee-Object -FilePath $SparkLog
    if ($LASTEXITCODE -ne 0) { throw "Spark/HDFS job failed for $Size messages. See $SparkLog" }
    if (-not (Test-Path $SummaryPath)) { throw "Spark job did not write summary JSON: $SummaryPath" }
    $Summary = Get-Content $SummaryPath -Raw | ConvertFrom-Json
    if ($Summary.status -ne 'PASS' -or [int]$Summary.valid_rows -ne $Size -or [int]$Summary.invalid_rows -ne 0 -or [int]$Summary.duplicate_engine_cycle_pairs -ne 0 -or [int]$Summary.cycle_order_warnings -ne 0) {
        throw "Data-quality/count check failed for $Size messages. Review $SummaryPath and $SparkLog"
    }

    $SparkSeconds = [double]$Summary.elapsed_seconds
    $EndToEndSeconds = $ProducerSeconds + $SparkSeconds
    $Rows += [pscustomobject]@{
        run_id = $RunId; dataset = $Dataset; split = $Split; requested_messages = $Size
        topic = $Topic; run_label = $RunLabel; delivered_messages = $Delivered
        producer_seconds = [math]::Round($ProducerSeconds, 3); producer_messages_per_second = [math]::Round($ProducerRate, 3)
        spark_hdfs_elapsed_seconds = $SparkSeconds; spark_hdfs_messages_per_second = [math]::Round($Size / [math]::Max($SparkSeconds, 0.001), 3)
        estimated_sequential_end_to_end_seconds = [math]::Round($EndToEndSeconds, 3)
        estimated_sequential_end_to_end_messages_per_second = [math]::Round($Size / [math]::Max($EndToEndSeconds, 0.001), 3)
        valid_rows = [int]$Summary.valid_rows; invalid_rows = [int]$Summary.invalid_rows
        duplicate_engine_cycle_pairs = [int]$Summary.duplicate_engine_cycle_pairs; cycle_order_warnings = [int]$Summary.cycle_order_warnings
        status = [string]$Summary.status; summary_json = $SummaryPath; producer_log = $ProducerLog; spark_log = $SparkLog
        limitations = 'Single configured Spark worker/DataNode; sequential producer then Spark drain; not a concurrent real-time or fault-recovery test.'
    }
    Write-Host "PASS $Size messages | Spark/HDFS elapsed $SparkSeconds sec | HDFS rows $($Summary.valid_rows)"
}

$CsvPath = Join-Path $ResultsDir 'streaming_scalability_benchmark.csv'
if (Test-Path $CsvPath) {
    $Prior = Import-Csv $CsvPath
    $AllRows = @($Prior) + @($Rows)
    $AllRows | Export-Csv -LiteralPath $CsvPath -NoTypeInformation
} else {
    $Rows | Export-Csv -LiteralPath $CsvPath -NoTypeInformation
}

$Latest = @($Rows | ForEach-Object { "| $($_.requested_messages) | $($_.valid_rows) | $($_.spark_hdfs_elapsed_seconds) | $($_.spark_hdfs_messages_per_second) | $($_.estimated_sequential_end_to_end_messages_per_second) | $($_.status) |" })
$Markdown = @(
    '# Phase 7 Streaming Replay/Drain Benchmark', '',
    "- Run ID: $RunId", "- Dataset: $Dataset/$Split", '- Kafka producer enqueued/delivered each requested message before Spark processing began.',
    '- Spark Structured Streaming validated JSON events and wrote Parquet to HDFS.',
    '- **Interpretation:** this measures controlled batch replay and drain, not simultaneous real-time ingest. The current stack is a single Spark worker and single HDFS DataNode; the result does not prove horizontal scaling or crash recovery.', '',
    '| Requested messages | Valid HDFS rows | Spark/HDFS seconds | Spark/HDFS rows/sec | Estimated sequential end-to-end rows/sec | Status |',
    '|---:|---:|---:|---:|---:|---|'
) + $Latest + @('', "Machine-readable history: `results/phase7/streaming_scalability_benchmark.csv`.", 'Detailed per-run Spark summaries are in `results/phase3/`; logs are in `results/phase7/`.')
$Markdown | Set-Content -LiteralPath (Join-Path $DocsDir 'phase7_streaming_benchmark_summary.md') -Encoding UTF8
Write-Host "`nPHASE 7 STREAMING SCALE BENCHMARK PASS"
Write-Host "CSV: $CsvPath"
Write-Host "Summary: $(Join-Path $DocsDir 'phase7_streaming_benchmark_summary.md')"
