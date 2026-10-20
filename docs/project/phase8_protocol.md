# Phase 8 Protocol — Frozen Official Test Evaluation

1. **Freeze first.** Preserve the Phase 7 variant choices and cap 125 for comparability. The cap is still provisional; mentor/team approval should be recorded before calling this a definitive final evaluation.
2. **Fit experts.** For each subset, train RF15, HGB15, RF30 and HGB30 on all labeled training engines using the fixed Phase 5 settings.
3. **Calibrate gates without test labels.** Generate five-fold GroupKFold OOF predictions with complete training engines held out (train/test engine IDs are partition-local and may overlap); train the four error gates on OOF absolute errors with engine-balanced sample weights.
4. **Predict test engines.** For each `test_features.parquet`, predict the final observed row per engine. Use the Phase 7 selected variant for that subset. Save prediction-only CSV first.
5. **Score once.** After prediction output has been written, read `test_targets.csv` and compute RMSE, MAE and NASA asymmetric score against the uncapped official test RUL values.
6. **Do not tune on official scores.** If an implementation bug requires a rerun, document it. Do not alter variants, cap, features or thresholds based on observed scores and continue calling that test set untouched.

## Frozen variant mapping

| Subset | Variant |
|---|---|
| FD001 | `cross_window_no_disagreement` |
| FD002 | `cross_window_error_gate` |
| FD003 | `cross_window_error_gate` |
| FD004 | `cross_window_no_disagreement` |

## Interpretation

Official test numbers are evidence for this specific frozen C-MAPSS run. They do not establish superiority on all engines, real aircraft, or operational maintenance settings. If the target cap was not agreed before scoring, treat results as exploratory and disclose that limitation.
