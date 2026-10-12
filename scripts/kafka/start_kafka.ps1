$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "docker\kafka\compose.yaml"

if (-not (Test-Path -LiteralPath $ComposeFile)) {
    throw "Compose file not found: $ComposeFile"
}

function Test-KafkaAdminReady {
    param([string]$ComposePath)

    # Run the readiness probe with stdout/stderr captured separately.
    # This prevents temporary Kafka startup warnings from terminating
    # the PowerShell script before its retry loop can continue.
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = (Get-Command docker.exe).Source
    $startInfo.Arguments = 'compose -f "' + $ComposePath +
        '" exec -T kafka kafka-topics.sh --bootstrap-server kafka:9093 --list'
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo

    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    if ($process.ExitCode -eq 0) {
        return $true
    }

    $script:LastKafkaProbeMessage = ($stderr + " " + $stdout).Trim()
    return $false
}

Write-Host "Starting DARE-RUL Kafka and ZooKeeper..."

& docker.exe compose -f $ComposeFile up -d

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start. Check Docker Desktop and Compose logs."
}

Write-Host "Waiting for Kafka to become ready (up to 90 seconds)..."

$script:LastKafkaProbeMessage = ""
$Ready = $false

for ($Attempt = 1; $Attempt -le 45; $Attempt++) {
    if (Test-KafkaAdminReady -ComposePath $ComposeFile) {
        $Ready = $true
        break
    }

    if ($Attempt % 5 -eq 0) {
        Write-Host "Still waiting... attempt $Attempt of 45"
    }

    Start-Sleep -Seconds 2
}

if (-not $Ready) {
    Write-Host "`nKafka readiness check failed."
    Write-Host "Last probe message: $script:LastKafkaProbeMessage"

    Write-Host "`n--- Compose status ---"
    & docker.exe compose -f $ComposeFile ps

    Write-Host "`n--- Kafka logs ---"
    & docker.exe logs --tail 80 dare-rul-kafka

    Write-Host "`n--- ZooKeeper logs ---"
    & docker.exe logs --tail 50 dare-rul-zookeeper

    throw "Kafka did not become ready. Share the status and logs above."
}

Write-Host "`nSUCCESS: Kafka is ready."
Write-Host "Container clients use kafka:9093."
Write-Host "Windows/Python clients use localhost:9092."

& docker.exe compose -f $ComposeFile ps
