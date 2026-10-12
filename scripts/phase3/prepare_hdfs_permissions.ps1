[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ComposeFile = Join-Path $ProjectRoot 'docker\phase3\compose.yaml'

if (-not (Test-Path -LiteralPath $ComposeFile)) {
    throw "Phase 3 Compose file not found: $ComposeFile"
}

function Invoke-HdfsDfs {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $HdfsArgs,
        [Parameter(Mandatory = $true)]
        [string] $Description
    )

    Write-Host "`n$Description"
    & docker.exe compose -f $ComposeFile exec -T namenode hdfs dfs @HdfsArgs
    if ($LASTEXITCODE -ne 0) {
        throw "HDFS command failed: hdfs dfs $($HdfsArgs -join ' ')"
    }
}

# Hadoop's `hdfs dfs` subcommands require a leading dash (e.g. -mkdir, not mkdir).
# Run these administrator operations inside the NameNode container. Do not alter
# the HDFS root permissions; only prepare the DARE-RUL project paths.
Invoke-HdfsDfs -HdfsArgs @('-mkdir', '-p', '/dare-rul') `
    -Description 'Ensuring the DARE-RUL HDFS root exists'

Invoke-HdfsDfs -HdfsArgs @('-chown', 'spark', '/dare-rul') `
    -Description 'Assigning the DARE-RUL root to the Spark job user'

Invoke-HdfsDfs -HdfsArgs @('-chmod', '755', '/dare-rul') `
    -Description 'Setting least-privilege project-root permissions'

Invoke-HdfsDfs -HdfsArgs @(
    '-mkdir', '-p', '/dare-rul/phase3', '/dare-rul/checkpoints/phase3'
) -Description 'Creating Phase 3 output and checkpoint parents'

Invoke-HdfsDfs -HdfsArgs @(
    '-chown', 'spark', '/dare-rul/phase3', '/dare-rul/checkpoints', '/dare-rul/checkpoints/phase3'
) -Description 'Assigning output and checkpoint parents to Spark'

Invoke-HdfsDfs -HdfsArgs @(
    '-chmod', '755', '/dare-rul/phase3', '/dare-rul/checkpoints', '/dare-rul/checkpoints/phase3'
) -Description 'Setting permissions on the Phase 3 parent directories'

Invoke-HdfsDfs -HdfsArgs @(
    '-ls', '-d', '/dare-rul', '/dare-rul/phase3', '/dare-rul/checkpoints', '/dare-rul/checkpoints/phase3'
) -Description 'Verifying HDFS owner and permissions'

Write-Host "`nSUCCESS: HDFS project directories are prepared for the Spark user."
Write-Host 'No HDFS volumes, existing run directories, or checkpoints were deleted.'
