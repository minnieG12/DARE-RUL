# Phase 7 Protocol

## Frozen inputs

- Phase 4 local training feature tables for FD001–FD004.
- Phase 5 engine-separated train/validation engine assignments and validation predictions.
- Phase 6 cross-fitted OOF expert predictions for Phase 5 training engines.
- Phase 6 validation metrics/predictions as existing comparators.

## Feature variants

- `multires_error_gate`: settings/current sensors plus both 15/30 rolling summaries; expert predictions and explicit disagreement summaries.
- `cross_window_error_gate`: the previous context plus 84 engineered per-sensor cross-window features; expert predictions and explicit disagreement summaries.
- `cross_window_no_disagreement`: enhanced sensor context and raw expert predictions, but no explicit mean/spread/range/deviation summaries.

All new error gates use fixed Phase 6 gate settings, seed 42, engine-balanced sample weights and OOF absolute-error targets. Validation labels do not train the gates.

## Metrics and diagnostics

- Row-weighted RMSE, MAE and PHM08/NASA score.
- Engine-macro RMSE, MAE and mean per-engine NASA score.
- Paired bootstrap confidence intervals for engine-macro metric differences. Negative candidate-minus-comparator differences favor the cross-window gate.
- Feature-group permutation deltas on validation: positive delta indicates the error worsened after the group was permuted.
- Sensor-feature perturbation stress test at 1% and 5% of training feature SD.
- Local in-process gate inference at 1×, 2× and 5× repeated validation rows.

## Interpretation rules

- Report gains only where measured and include adverse metrics/subsets.
- The current validation cohort was already used in Phase 5/6 comparisons; Phase 7 is exploratory, not an independent test.
- Official test labels remain unused until the target cap, features, selection rules and metrics are frozen after Phase 1 protocol review.
- Synthetic feature noise does not represent a physically validated sensor fault. Inference timing does not prove distributed scalability.
