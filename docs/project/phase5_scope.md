# Phase 5 Scope — Classical ML Baselines

## Goal
Establish reproducible single-model baselines on the Phase 4 multi-resolution features before building the Phase 6 adaptive ensemble.

## Models
- RF15: Random Forest using current operating settings, raw sensor values and 15-cycle rolling statistics.
- HGB15: HistGradientBoostingRegressor using the same 15-cycle feature view.
- RF30: Random Forest using the 30-cycle feature view.
- HGB30: HistGradientBoostingRegressor using the same 30-cycle feature view.

These are reference baselines for this project, not exact replications of any named paper. Do not describe them as paper reproductions until the closest papers and their configurations have been reviewed.

## Split and labels
- Use a fixed 80/20 validation split by engine (`GroupShuffleSplit`, seed 42).
- All cycle rows from one engine remain entirely in train or validation.
- Primary run caps the training and validation targets at 125 cycles, a common C-MAPSS convention. This is provisional pending literature review and mentor/team confirmation; a capped-versus-uncapped sensitivity analysis should be recorded before final publication claims.
- `engine_id` and `cycle` are identifiers/order keys and are excluded from model predictors.
- Official `test_FDxxx.txt` and `RUL_FDxxx.txt` files are not read by this phase. Do not select models based on official test labels.

## Features
For each window, input columns are the three operating settings, 21 current sensor values, and 63 features from sensor rolling means, population standard deviations and deltas for the chosen window. This gives 87 predictors per window.

## Metrics
Report RMSE, MAE and the PHM08/NASA asymmetric score. Error is prediction minus truth; over-predicting remaining life receives the steeper `exp(error/10)-1` penalty, while under-predicting uses `exp(-error/13)-1`. Lower is better.

## Limits
This phase establishes fixed-model validation references only. It does not evaluate official test scores, establish novelty, perform hyperparameter search, or measure distributed scalability. Validation metrics are computed over all cycle rows of held-out engines; row-level scores are not directly interchangeable with official test metrics that use one terminal observation per test engine.
