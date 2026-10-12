param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$UpdateRoot = Join-Path $ProjectRoot "docs_cleanup_update"
$CurrentProjectDocs = Join-Path $ProjectRoot "docs\project"

$RemoveProjectDocs = @(
    "phase2_run_summary.txt",
    "phase2_run_summary_template.md",
    "phase3_run_summary_template.md",
    "phase3_hdfs_permissions_fix.md"
)

$RemoveRootDocs = @(
    "README_PHASE0_1.md",
    "README_PHASE1.md",
    "README_PHASE2.md",
    "README_PHASE2_COMPLETION.md",
    "README_PHASE3.md",
    "README_PHASE3_IVY_FIX.md",
    "README_PHASE3_HDFS_PERMISSION_FIX.md",
    "README_PHASE3.txt"
)

if (-not (Test-Path (Join-Path $UpdateRoot "docs\project\phase3_run_summary.md"))) {
    throw "Cleanup update files not found. Extract the ZIP at the project root first."
}

Write-Host "Project: $ProjectRoot"
Write-Host "This cleanup keeps the literature directory and other unlisted project docs."
Write-Host "It will replace README.md plus phase1 checklist/exit notes, Phase 2 summary, Phase 3 runbook/summary/troubleshooting, and research_log.md."
Write-Host "It will remove only these duplicates after creating a local backup:"
$RemoveProjectDocs | ForEach-Object { Write-Host "  docs\project\$_" }
$RemoveRootDocs | ForEach-Object { Write-Host "  $_" }

if (-not $Apply) {
    Write-Host "`nPREVIEW ONLY. Review the list above, then rerun with -Apply to back up, update and remove these files."
    exit 0
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $ProjectRoot "results\docs_cleanup_backup_$Stamp"
$BackupProject = Join-Path $BackupRoot "docs_project"
$BackupRootDocs = Join-Path $BackupRoot "root_phase_readmes"
New-Item -ItemType Directory -Force -Path $BackupProject, $BackupRootDocs | Out-Null

if (Test-Path $CurrentProjectDocs) {
    Get-ChildItem -LiteralPath $CurrentProjectDocs -Force |
        Copy-Item -Destination $BackupProject -Recurse -Force
}
foreach ($name in $RemoveRootDocs) {
    $path = Join-Path $ProjectRoot $name
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Copy-Item -LiteralPath $path -Destination $BackupRootDocs -Force
    }
}
$RootReadme = Join-Path $ProjectRoot "README.md"
if (Test-Path -LiteralPath $RootReadme -PathType Leaf) {
    Copy-Item -LiteralPath $RootReadme -Destination $BackupRootDocs -Force
}

Write-Host "`nBackup created at: $BackupRoot"

# Copy curated top-level README.
Copy-Item -LiteralPath (Join-Path $UpdateRoot "README.md") -Destination $RootReadme -Force

# Copy updated project docs while preserving other docs (especially literature files).
$UpdateProjectDocs = Join-Path $UpdateRoot "docs\project"
Get-ChildItem -LiteralPath $UpdateProjectDocs -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($UpdateProjectDocs.Length).TrimStart('\','/')
    $destination = Join-Path $CurrentProjectDocs $relative
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
}

foreach ($name in $RemoveProjectDocs) {
    $path = Join-Path $CurrentProjectDocs $name
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "Removed duplicate: docs\project\$name"
    }
}

foreach ($name in $RemoveRootDocs) {
    $path = Join-Path $ProjectRoot $name
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "Removed old phase README: $name"
    }
}

Remove-Item -LiteralPath $UpdateRoot -Recurse -Force
$InstructionPath = Join-Path $ProjectRoot "CLEANUP_INSTRUCTIONS.md"
if (Test-Path -LiteralPath $InstructionPath -PathType Leaf) {
    Remove-Item -LiteralPath $InstructionPath -Force
}
Write-Host "`nCleanup applied. Backup preserved at: $BackupRoot"
Write-Host "Review git status before committing. No data, code, Docker files or HDFS volumes were changed."
