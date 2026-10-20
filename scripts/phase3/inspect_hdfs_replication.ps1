[CmdletBinding()]
param(
    [string]$NameNodeContainer = "dare-rul-namenode",
    [string]$HdfsPath = "/dare-rul"
)
$ErrorActionPreference = "Stop"
Write-Host "Configured dfs.replication:" -ForegroundColor Cyan
docker exec $NameNodeContainer hdfs getconf -confKey dfs.replication
if ($LASTEXITCODE -ne 0) { throw "Could not read dfs.replication" }
Write-Host "HDFS summary:" -ForegroundColor Cyan
docker exec $NameNodeContainer hdfs dfsadmin -report
if ($LASTEXITCODE -ne 0) { throw "dfsadmin -report failed" }
Write-Host "Filesystem check (this inspects; it does not change replication): $HdfsPath" -ForegroundColor Cyan
docker exec $NameNodeContainer hdfs fsck $HdfsPath -files -blocks -locations
if ($LASTEXITCODE -ne 0) { throw "fsck reported a command-level failure; review its full output" }
Write-Host "Inspection finished. No files or replication settings were changed." -ForegroundColor Green
