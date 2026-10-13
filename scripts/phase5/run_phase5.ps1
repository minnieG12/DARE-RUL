$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..\..'))
$Python = Join-Path $PWD '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    throw "Project Python environment not found at $Python. Run this from the existing DARE-RUL project and create .venv first."
}
Write-Host 'DARE-RUL Phase 5: running the baseline unit tests first' -ForegroundColor Cyan
& $Python -m pytest .\tests\test_phase5_baselines.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Running fixed Random Forest and HistGradientBoosting baselines' -ForegroundColor Cyan
& $Python .\scripts\phase5\run_phase5.py --rul-cap 125 --seed 42 --validation-fraction 0.2 --trees 120 --max-iter 150
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Phase 5 run finished. Review docs\project\phase5_run_summary.md.' -ForegroundColor Green
