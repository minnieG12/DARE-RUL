$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Compose = Join-Path $Root "docker\phase3\compose.yaml"

Write-Host "--- Services ---"
& docker.exe compose -f $Compose ps
Write-Host "`n--- Spark Master version ---"
& docker.exe compose -f $Compose exec -T spark-master /opt/spark/bin/spark-submit --version
Write-Host "`n--- HDFS report ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfsadmin -report
Write-Host "`n--- HDFS root ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfs -ls /
