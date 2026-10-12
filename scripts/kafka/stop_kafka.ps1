$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ComposeFile = Join-Path $ProjectRoot "docker\kafka\compose.yaml"
Write-Host "Stopping containers but preserving Kafka/ZooKeeper volumes..."
docker compose -f $ComposeFile down
if ($LASTEXITCODE -ne 0) { throw "Compose shutdown failed." }
Write-Host "Stopped. Named volumes were preserved. Do not use --volumes unless intentionally deleting Kafka state."
