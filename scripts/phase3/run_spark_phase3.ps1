param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')][string]$Topic,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')][string]$RunLabel,
    [ValidateRange(0,10000000)][int]$ExpectedMessages = 500,
    [ValidateRange(1,1000000)][int]$MaxOffsetsPerTrigger = 200
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Compose = Join-Path $Root "docker\phase3\compose.yaml"
$JobScript = "/opt/phase3/kafka_to_hdfs.py"

$Networks = @(& docker.exe network ls --format "{{.Name}}")
if ($Networks -notcontains "dare-rul-phase2_dare-rul-net") {
    throw "Kafka network not found. Start the Phase 2 Kafka stack first."
}

Write-Host "Spark will read topic: $Topic"
Write-Host "Unique run label: $RunLabel"
Write-Host "Expected messages: $ExpectedMessages"
Write-Host "Submitting a Spark Structured Streaming job to spark://spark-master:7077..."

$PreviousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & docker.exe compose -f $Compose --profile job run --rm spark-job `
        --master spark://spark-master:7077 `
        --deploy-mode client `
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 `
        --conf spark.executor.instances=1 `
        --conf spark.executor.cores=2 `
        --conf spark.executor.memory=2g `
        --conf spark.driver.memory=2g `
        $JobScript `
        --topic $Topic `
        --run-label $RunLabel `
        --expected-messages $ExpectedMessages `
        --max-offsets-per-trigger $MaxOffsetsPerTrigger
    $DockerExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
}

if ($DockerExitCode -ne 0) {
    throw "Spark job failed with Docker exit code $DockerExitCode. Review the benchmark Spark log. Use a new RunLabel for a retry; do not delete HDFS checkpoints blindly."
}
Write-Host "Spark job exited successfully. Run the HDFS output verification script next."
