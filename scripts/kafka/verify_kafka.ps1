$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "docker\kafka\compose.yaml"
Write-Host "Compose services:"
docker compose -f $ComposeFile ps
if ($LASTEXITCODE -ne 0) { throw "Could not query Compose services." }
Write-Host "Topic details:"
docker compose -f $ComposeFile exec -T kafka kafka-topics.sh --bootstrap-server kafka:9093 --describe --topic cmapss-telemetry
if ($LASTEXITCODE -ne 0) { throw "Topic not found. Run create_topic.ps1 first." }
Write-Host "Broker/topic verification completed."
