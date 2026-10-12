$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Project virtual environment not found at $Python. From repository root run: py -3.10 -m venv .venv, then install the project's requirements."
}
Write-Host "DARE-RUL Phase 4: run focused unit tests first" -ForegroundColor Cyan
& $Python -m pytest .\tests\test_phase4_features.py -q
if ($LASTEXITCODE -ne 0) { throw "Phase 4 unit tests failed. Fix these before building the features." }
Write-Host "Building FD001-FD004 multi-resolution features" -ForegroundColor Cyan
& $Python .\scripts\features\build_phase4_features.py --data-dir .\data\CMAPSSData --output-dir .\data\features\phase4 --subsets FD001 FD002 FD003 FD004 --windows 15 30
if ($LASTEXITCODE -ne 0) { throw "Phase 4 feature build failed. Read the error above and correct the input/dependency issue." }
Write-Host "Writing the curated Phase 4 run summary" -ForegroundColor Cyan
& $Python .\scripts\phase4\write_phase4_summary.py --summary .\data\features\phase4\phase4_build_summary.json --output .\docs\project\phase4_run_summary.md
if ($LASTEXITCODE -ne 0) { throw "Could not generate docs\project\phase4_run_summary.md" }
Write-Host "Phase 4 feature generation completed. Review docs\project\phase4_run_summary.md and data\features\phase4\phase4_build_summary.json" -ForegroundColor Green
