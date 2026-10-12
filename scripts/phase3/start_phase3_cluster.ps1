$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Compose = Join-Path $Root "docker\phase3\compose.yaml"
$NetworkName = "dare-rul-phase2_dare-rul-net"

$Networks = @(& docker.exe network ls --format "{{.Name}}")
if ($LASTEXITCODE -ne 0) { throw "Could not query Docker networks. Is Docker Desktop running?" }
if ($Networks -notcontains $NetworkName) {
    throw "Required Kafka network '$NetworkName' was not found. Start Kafka with .\scripts\kafka\start_kafka.ps1 and retry."
}

Write-Host "Starting Spark Master/Worker and HDFS NameNode/DataNode..."
& docker.exe compose -f $Compose up -d spark-master spark-worker namenode datanode
if ($LASTEXITCODE -ne 0) { throw "Could not start Phase 3 services. Review Docker output." }

Write-Host "Waiting for HDFS to become ready..."
$Ready = $false
for ($i = 1; $i -le 40; $i++) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command docker.exe).Source
    $psi.Arguments = "compose -f `"$Compose`" exec -T namenode hdfs dfs -ls /"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    if ($proc.ExitCode -eq 0) { $Ready = $true; break }
    if ($i % 5 -eq 0) { Write-Host "HDFS is still starting ($i/40)..." }
    Start-Sleep -Seconds 3
}

if (-not $Ready) {
    & docker.exe compose -f $Compose ps
    & docker.exe compose -f $Compose logs --tail 60 namenode datanode
    throw "HDFS did not become ready within about 120 seconds. Share the output above."
}

Write-Host "Phase 3 services started. HDFS is responding."
& docker.exe compose -f $Compose ps
Write-Host "Spark Master UI: http://localhost:8080"
Write-Host "Spark Worker UI: http://localhost:8081"
Write-Host "HDFS NameNode UI: http://localhost:9870"
