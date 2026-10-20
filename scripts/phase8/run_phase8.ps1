param(
    [int]$RulCap = 125,
    [int]$OofFolds = 5,
    [switch]$ProtocolApproved,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    throw "Project Python environment not found: $Python. Create/activate the project .venv first."
}

Push-Location $RepoRoot
try {
    Write-Host '=== Phase 8 unit tests ===' -ForegroundColor Cyan
    & $Python -m pytest .\tests\test_phase8_final_eval.py -q
    if ($LASTEXITCODE -ne 0) { throw "Phase 8 tests failed with exit code $LASTEXITCODE" }

    Write-Host '=== Phase 8 official test evaluation ===' -ForegroundColor Cyan
    $ArgsList = @('.\scripts\phase8\run_phase8.py', '--rul-cap', "$RulCap", '--oof-folds', "$OofFolds")
    if ($ProtocolApproved) { $ArgsList += '--protocol-approved' }
    if ($Overwrite) { $ArgsList += '--overwrite' }
    & $Python @ArgsList
    if ($LASTEXITCODE -ne 0) { throw "Phase 8 evaluation failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
