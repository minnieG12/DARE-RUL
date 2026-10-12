param(
    [ValidateRange(1, 100000)][int]$MessagesPerScenario = 500,
    [ValidateRange(0, 100000)][double]$Rate = 100
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "docker\kafka\compose.yaml"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Producer = Join-Path $ProjectRoot "scripts\kafka\cmapss_producer.py"
$Consumer = Join-Path $ProjectRoot "scripts\kafka\cmapss_consumer.py"
$Docker = (Get-Command docker.exe -ErrorAction Stop).Source
$RunId = Get-Date -Format "yyyyMMddHHmmssfff"
$LogDir = Join-Path $ProjectRoot "results\phase2\matrix_$RunId"
$MachineResults = Join-Path $LogDir "matrix_results.csv"
$TrackedResults = Join-Path $ProjectRoot "docs\project\phase2_matrix_results.csv"

foreach ($RequiredPath in @($ComposeFile, $Python, $Producer, $Consumer)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required file not found: $RequiredPath"
    }
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function ConvertTo-QuotedArgument {
    param([string]$Value)
    # All arguments are quoted so paths containing spaces work on Windows.
    return '"' + $Value.Replace('"', '\"') + '"'
}

function Invoke-LoggedProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPrefix
    )
    $StdoutPath = "$LogPrefix.stdout.txt"
    $StderrPath = "$LogPrefix.stderr.txt"
    $Quoted = @($Arguments | ForEach-Object { ConvertTo-QuotedArgument ([string]$_) })
    $ArgumentLine = $Quoted -join " "
    $Process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentLine `
        -WorkingDirectory $ProjectRoot `
        -PassThru -Wait -NoNewWindow `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath

    $Stdout = if (Test-Path $StdoutPath) { Get-Content -LiteralPath $StdoutPath -Raw } else { "" }
    $Stderr = if (Test-Path $StderrPath) { Get-Content -LiteralPath $StderrPath -Raw } else { "" }
    return [pscustomobject]@{
        ExitCode = $Process.ExitCode
        Stdout = $Stdout
        Stderr = $Stderr
        StdoutPath = $StdoutPath
        StderrPath = $StderrPath
    }
}

Write-Host "Checking Kafka broker before the matrix..."
$Probe = Invoke-LoggedProcess -FilePath $Docker -Arguments @(
    "compose", "-f", $ComposeFile, "exec", "-T", "kafka",
    "kafka-topics.sh", "--bootstrap-server", "kafka:9093", "--list"
) -LogPrefix (Join-Path $LogDir "broker_probe")
if ($Probe.ExitCode -ne 0) {
    Write-Host $Probe.Stdout
    Write-Host $Probe.Stderr
    throw "Kafka is not ready. Start it with .\scripts\kafka\start_kafka.ps1 and rerun the matrix."
}

$Results = @()
$Invariant = [System.Globalization.CultureInfo]::InvariantCulture
$RateText = $Rate.ToString($Invariant)

foreach ($Dataset in @("FD001", "FD002", "FD003", "FD004")) {
    foreach ($Split in @("train", "test")) {
        $Topic = "cmapss-p2-$($Dataset.ToLower())-$Split-$RunId"
        Write-Host "`n=== $Dataset / $Split | topic $Topic ===" -ForegroundColor Cyan

        $Create = Invoke-LoggedProcess -FilePath $Docker -Arguments @(
            "compose", "-f", $ComposeFile, "exec", "-T", "kafka",
            "kafka-topics.sh", "--bootstrap-server", "kafka:9093",
            "--create", "--topic", $Topic, "--partitions", "4", "--replication-factor", "1"
        ) -LogPrefix (Join-Path $LogDir "$Dataset-$Split-topic")
        if ($Create.ExitCode -ne 0) {
            Write-Host $Create.Stdout
            Write-Host $Create.Stderr
            $Results += [pscustomobject]@{
                run_id=$RunId; dataset=$Dataset; split=$Split; topic=$Topic
                requested=$MessagesPerScenario; enqueued=0; delivered=0; producer_failed=-1
                outstanding=-1; producer_rate=0; read=0; valid=0; consumer_invalid=-1
                ordering_warnings=-1; consumer_rate=0; producer_exit=$null; consumer_exit=$null; status="FAIL_TOPIC_CREATE"
            }
            continue
        }

        # Allow a new topic's metadata/leader state to settle before producer startup.
        Start-Sleep -Seconds 2
        $ProducerResult = Invoke-LoggedProcess -FilePath $Python -Arguments @(
            $Producer, "--dataset", $Dataset, "--split", $Split,
            "--topic", $Topic, "--rate", $RateText,
            "--max-messages", ([string]$MessagesPerScenario)
        ) -LogPrefix (Join-Path $LogDir "$Dataset-$Split-producer")
        $POutput = $ProducerResult.Stdout + "`n" + $ProducerResult.Stderr
        $PDelivery = [regex]::Match($POutput, 'Delivered:\s*(\d+);\s*failed:\s*(\d+);\s*outstanding after flush:\s*(\d+)')
        $PEnqueued = [regex]::Match($POutput, 'Rows selected / messages enqueued:\s*(\d+)\s*/\s*(\d+)')
        $PRate = [regex]::Match($POutput, 'achieved delivery rate:\s*([\d.]+)\s*messages/sec')

        $Enqueued = if ($PEnqueued.Success) { [int]$PEnqueued.Groups[2].Value } else { 0 }
        $Delivered = if ($PDelivery.Success) { [int]$PDelivery.Groups[1].Value } else { 0 }
        $PFailed = if ($PDelivery.Success) { [int]$PDelivery.Groups[2].Value } else { -1 }
        $Outstanding = if ($PDelivery.Success) { [int]$PDelivery.Groups[3].Value } else { -1 }
        $ProducerRate = if ($PRate.Success) { [double]::Parse($PRate.Groups[1].Value, $Invariant) } else { 0 }

        $Read = 0; $Valid = 0; $CInvalid = -1; $Ordering = -1; $ConsumerRate = 0; $ConsumerExit = $null
        if ($ProducerResult.ExitCode -eq 0 -and $Delivered -eq $MessagesPerScenario -and $PFailed -eq 0 -and $Outstanding -eq 0) {
            $ConsumerResult = Invoke-LoggedProcess -FilePath $Python -Arguments @(
                $Consumer, "--topic", $Topic, "--max-messages", ([string]$MessagesPerScenario), "--idle-timeout", "20"
            ) -LogPrefix (Join-Path $LogDir "$Dataset-$Split-consumer")
            $ConsumerExit = $ConsumerResult.ExitCode
            $COutput = $ConsumerResult.Stdout + "`n" + $ConsumerResult.Stderr
            $CCounts = [regex]::Match($COutput, 'Read:\s*(\d+);\s*valid:\s*(\d+);\s*invalid/broker errors:\s*(\d+);\s*ordering warnings:\s*(\d+)')
            $CRate = [regex]::Match($COutput, 'Observed read rate:\s*([\d.]+)\s*messages/sec')
            if ($CCounts.Success) {
                $Read = [int]$CCounts.Groups[1].Value
                $Valid = [int]$CCounts.Groups[2].Value
                $CInvalid = [int]$CCounts.Groups[3].Value
                $Ordering = [int]$CCounts.Groups[4].Value
            }
            if ($CRate.Success) { $ConsumerRate = [double]::Parse($CRate.Groups[1].Value, $Invariant) }
        }

        $Status = "PASS"
        if ($ProducerResult.ExitCode -ne 0 -or $Delivered -ne $MessagesPerScenario -or $PFailed -ne 0 -or $Outstanding -ne 0) {
            $Status = "FAIL_PRODUCER"
        } elseif ($ConsumerExit -ne 0 -or $Read -ne $MessagesPerScenario -or $Valid -ne $MessagesPerScenario -or $CInvalid -ne 0 -or $Ordering -ne 0) {
            $Status = "FAIL_CONSUMER"
        }

        $Results += [pscustomobject]@{
            run_id=$RunId; dataset=$Dataset; split=$Split; topic=$Topic
            requested=$MessagesPerScenario; enqueued=$Enqueued; delivered=$Delivered
            producer_failed=$PFailed; outstanding=$Outstanding; producer_rate=$ProducerRate
            read=$Read; valid=$Valid; consumer_invalid=$CInvalid; ordering_warnings=$Ordering
            consumer_rate=$ConsumerRate; producer_exit=$ProducerResult.ExitCode
            consumer_exit=$ConsumerExit; status=$Status
        }

        Write-Host "$Dataset/$Split : $Status | delivered=$Delivered | valid=$Valid | ordering_warnings=$Ordering"
        if ($Status -ne "PASS") {
            Write-Warning "Scenario logs: $LogDir"
        }
    }
}

$Results | Export-Csv -LiteralPath $MachineResults -NoTypeInformation -Encoding UTF8
$Results | Export-Csv -LiteralPath $TrackedResults -NoTypeInformation -Encoding UTF8

$PassCount = @($Results | Where-Object status -eq "PASS").Count
Write-Host "`nMatrix complete: $PassCount / $($Results.Count) scenarios passed."
Write-Host "Machine log/results: $LogDir"
Write-Host "Git-trackable results: $TrackedResults"
$Results | Format-Table dataset, split, delivered, valid, producer_rate, consumer_rate, status -AutoSize

if ($PassCount -ne 8) {
    throw "One or more Phase 2 scenarios failed. Review the per-scenario stdout/stderr logs before committing a completion status."
}
Write-Host "Phase 2 expanded dataset/split matrix passed. This is still a smoke/ingestion test, not the scalability study." -ForegroundColor Green
