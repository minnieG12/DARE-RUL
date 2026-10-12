param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')][string]$RunLabel
)
$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Compose = Join-Path $Root "docker\phase3\compose.yaml"
$ParquetPath = "/dare-rul/phase3/$RunLabel/parquet"
$InvalidPath = "/dare-rul/phase3/$RunLabel/invalid"
$CheckpointPath = "/dare-rul/checkpoints/phase3/$RunLabel"

Write-Host "--- Valid Parquet output ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfs -ls -h $ParquetPath
Write-Host "`n--- Invalid-record output (may be empty) ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfs -ls -h $InvalidPath
Write-Host "`n--- Checkpoint paths ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfs -ls -R $CheckpointPath
Write-Host "`n--- HDFS file/size counts ---"
& docker.exe compose -f $Compose exec -T namenode hdfs dfs -count -h $ParquetPath
