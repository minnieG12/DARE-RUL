# Phase 4 Runbook

## Run from repository root (PowerShell)

```powershell
.\scripts\phase4\run_phase4.ps1
```

The script runs the five small feature tests first. If they pass, it builds features for FD001, FD002, FD003 and FD004 using trailing 15- and 30-cycle windows. The default output is local under `data/features/phase4/` and should remain excluded from Git.

## Verify outputs

```powershell
Get-Content .\data\features\phase4\phase4_build_summary.json
Get-ChildItem .\data\features\phase4 -Recurse
Get-Content .\data\features\phase4\FD001\metadata.json
```

For every FD subset, expect `train_features.parquet`, `test_trajectory_features.parquet`, `test_features.parquet`, `test_targets.csv`, and `metadata.json`.

## Expected meaning

- Train rows = all observed training cycles across engines.
- Test trajectory rows = all observed test cycles across engines.
- Test final rows = number of test engines (one prediction point per engine).
- Train RUL is uncapped unless a positive `--rul-cap` is explicitly given.
- `test_targets.csv` is ground truth for later final evaluation, not for feature generation or model/gate tuning.
- Keep `engine_id` as an identifier, not a predictive input; it identifies which engine a row belongs to.

## If it fails

- `Input file not found`: check the raw files are under `data\CMAPSSData` and names match `train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt`, etc.
- `Parquet support is missing`: activate `.venv` and run `python -m pip install pyarrow`.
- `No module named pytest`: run `python -m pip install pytest` in `.venv`.
- `expected 26 columns`: likely the wrong file/path or a malformed input file; do not edit raw files to make the error disappear.
- Non-finite or duplicate pair error: stop and investigate the source file; do not silently drop records.

## Research caution
The `PASS` status means the feature-generation job ran and its internal checks passed. It does not say that any model is accurate or the proposed ensemble is better. Record the final RUL cap and evaluation protocol after mentor/team agreement in Phase 1.
