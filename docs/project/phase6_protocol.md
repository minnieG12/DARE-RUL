# Phase 6 Protocol — Candidate Adaptive Gate

This is a pre-run protocol note. It describes the candidate blend to be evaluated; it does not assert that the method is novel or better.

## Experts

- RF15: Random Forest using the 15-cycle features.
- HGB15: Histogram Gradient Boosting using the 15-cycle features.
- RF30: Random Forest using the 30-cycle features.
- HGB30: Histogram Gradient Boosting using the 30-cycle features.

Expert estimator settings inherit the fixed settings in `scripts/phase5/baseline_core.py`.

## Comparators

- Individual experts.
- Equal-weight average.
- Static inverse-OOF-engine-macro-MAE weights, calculated using only out-of-fold predictions from Phase 5 training engines.
- Adaptive per-row gate. Each expert's expected absolute error is learned from the same cross-fitted training-only records. Each gate receives 30-cycle sensor/settings context, all four expert predictions, their mean/spread/range, and each expert's absolute deviation from the mean. Predicted errors are clipped at zero, shifted by a fixed 0.5-cycle floor and converted to normalized inverse-error weights.

## Data separation

The existing Phase 5 held-out engines remain the evaluation cohort. Gate training only uses OOF predictions from Phase 5 training engines. The official test files/targets are not loaded.

## Metrics

Report RMSE, MAE and PHM08/NASA asymmetric score using the same sign convention and cap as Phase 5, plus engine-macro RMSE, MAE and mean per-engine score. Row-weighted metrics allow direct comparison with Phase 5; engine-macro metrics give each engine equal influence.

## Decision rule

Do not claim success because one metric or one subset improves. Compare all subsets and all metrics with the simple averaging baseline. Treat any observed gain as preliminary until the study has a separate frozen final test evaluation, ablations and a full related-work review.
