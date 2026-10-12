$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "docker\kafka\compose.yaml"
docker compose -f $ComposeFile exec -T kafka kafka-topics.sh --bootstrap-server kafka:9093 --create --if-not-exists --topic cmapss-telemetry --partitions 4 --replication-factor 1
if ($LASTEXITCODE -ne 0) { throw "Topic creation failed. Ensure Kafka is running first." }
Write-Host "Topic cmapss-telemetry is configured for four partitions and replication factor one (single-broker demo)."
