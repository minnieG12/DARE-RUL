$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project virtualenv not found at $Python" }
Write-Host "DARE-RUL Phase 6: run focused unit tests first"
& $Python -m pytest .\tests\test_phase6_ensemble.py -q
if ($LASTEXITCODE -ne 0) { throw "Phase 6 unit tests failed; fix them before running the ensemble." }
Write-Host "Running Phase 6 OOF-calibrated adaptive ensemble. This may take a while (many RF fits)."
& $Python .\scripts\phase6\run_phase6.py
if ($LASTEXITCODE -ne 0) { throw "Phase 6 experiment failed; preserve the output and inspect the error." }
Write-Host "Phase 6 run finished. Review docs\project\phase6_run_summary.md."
