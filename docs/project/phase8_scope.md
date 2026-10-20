# Phase 8 Scope — Official Test Evaluation and Maintenance Demo

## Goals

1. Produce one frozen official test evaluation for FD001–FD004 using the selected Phase 7 variants.
2. Fit the four Phase 5 experts on all labeled training engines for each subset.
3. Fit the Phase 7-style expected-error gates using engine-grouped out-of-fold predictions generated only from labeled training engines.
4. Save one prediction per official test engine, then load official RUL targets solely to calculate final metrics.
5. Provide an illustrative maintenance-priority CSV and optional Streamlit dashboard driven by predictions only.

## Frozen method selection

- FD001: `cross_window_no_disagreement`
- FD002: `cross_window_error_gate`
- FD003: `cross_window_error_gate`
- FD004: `cross_window_no_disagreement`

These choices are frozen from prior Phase 7 validation comparisons. Official test metrics must not be used to change these choices and then be reported as an untouched test evaluation.

## RUL cap

The training target cap defaults to 125 to match Phases 5–7. That cap remains provisional until the Phase 1 research protocol is reviewed and approved. The script keeps official test RUL labels uncapped for scoring and clips model predictions to [0, 125]. If the cap was not agreed before this run, report the resulting metrics as exploratory rather than a definitive final claim.

## Separation and leakage protection

- `engine_id`, `cycle`, and `RUL` are excluded from model features.
- Every OOF split holds out complete training engines. C-MAPSS reuses numeric engine IDs separately inside train and test partitions, so matching IDs across those files are normal.
- Gate fitting uses only OOF predictions and training targets.
- `test_predictions.csv` is written before `test_targets.csv` is read for scoring.
- Official test targets are not used for fitting, gate calibration or method selection.
- The demo consumes `test_predictions.csv` only and rejects scored files that contain ground-truth labels.

## Metrics

Report RMSE, MAE, and PHM08/NASA asymmetric score (sum and mean), separately for FD001–FD004. Lower is better for all three metrics under the metric definition used in Phases 5–7. Keep per-engine scored rows for auditing.

## Limits

The result is from the C-MAPSS benchmark, not real aircraft. Risk bands in the demo are illustrative thresholds, not maintenance policy or safety guidance. The official test cohort should not be reused for repeated tuning.
