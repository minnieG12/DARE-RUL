$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project Python environment not found: $Python" }
Write-Host "DARE-RUL Phase 7: run focused tests first"
& $Python -m pytest .\tests\test_phase7_experiments.py -q
if ($LASTEXITCODE -ne 0) { throw "Phase 7 tests failed; do not start experiments" }
Write-Host "Running feature ablations, robustness, bootstrap CIs, explainability and inference timing"
& $Python .\scripts\phase7\run_phase7.py
if ($LASTEXITCODE -ne 0) { throw "Phase 7 experiment failed; preserve the full output" }
Write-Host "Phase 7 run completed. Review docs\project\phase7_run_summary.md"
