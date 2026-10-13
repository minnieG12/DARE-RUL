# Phase 6 Runbook

## Prerequisites

- Phase 4 feature data exists under `data/features/phase4/FD001` through `FD004`.
- Phase 5 has completed and saved local artifacts under `models/phase5/` and `results/phase5/`.
- Python environment contains NumPy, pandas, PyArrow, scikit-learn, joblib and pytest.

## Run

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_phase6_ensemble.py -q
.\scripts\phase6\run_phase6.ps1
```

The OOF fit repeats the four Phase 5 experts across four GroupKFold folds for each dataset subset. Random Forest fits take the most time; allow the job to finish and do not launch multiple copies in parallel.

## Outputs (local and ignored)

- `results/phase6/validation_metrics.csv` — 7 methods per subset (28 rows for all four subsets).
- `results/phase6/validation_predictions.csv` — validation predictions and adaptive per-row weights.
- `results/phase6/oof_reliability.csv` — training-only OOF engine-macro MAE and static ensemble weights.
- `results/phase6/run_metadata.json` — settings and leakage guard statements.
- `results/phase6/<subset>/oof_predictions.csv` — cross-fitted predictions on Phase 5 training engines.
- `results/phase6/<subset>/adaptive_expected_errors_validation.csv` — gate estimates on validation rows.
- `models/phase6/<subset>/error_gate_*.joblib` and `ensemble_weights.json` — fitted gate artifacts.
- `docs/project/phase6_run_summary.md` — generated readable report.

Do not add `results/phase6/` or `models/phase6/` to Git. Existing root `.gitignore` rules should already ignore them.

## Success checks

- All Phase 6 unit tests pass.
- Script reports `PHASE 6 ADAPTIVE ENSEMBLE RUN PASS`.
- `validation_metrics.csv` contains 28 rows total (7 methods × 4 subsets).
- Each subset has 7 method rows, all with finite RMSE/MAE/score values.
- Metadata says `official_test_targets_used: false`.
- Report shows individual experts, equal average, OOF inverse-MAE weighted blend and adaptive gate results.

## Interpretation

A lower validation metric is evidence only for this split and setup. If the adaptive method fails to beat simple averaging consistently, report that honestly and investigate; do not tune repeatedly on the held-out validation engines. Official test labels remain reserved for a frozen, later evaluation protocol.
