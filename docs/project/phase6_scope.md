# Phase 6 Scope — OOF-Calibrated Adaptive Ensemble

## Goal

Build a candidate ensemble from the four Phase 5 experts (`RF15`, `HGB15`, `RF30`, `HGB30`) and compare it against individual experts and simple blending baselines on the same held-out engines used in Phase 5.

## Methods compared

1. The four individual Phase 5 experts.
2. Equal-weight average of the four experts.
3. Fixed inverse-error weighted average. Its weights are computed from per-engine MAE on out-of-fold (OOF) predictions of the Phase 5 training engines only.
4. Adaptive error-gated blend. Four small HistGradientBoosting models predict each expert's absolute error from (a) 30-cycle context features, (b) all four expert predictions, and (c) expert spread/range/deviation. Predicted errors become normalized inverse-error weights for that row.

## Leakage controls

- Reuses Phase 5's stored engine split and already-generated Phase 5 validation predictions.
- Creates OOF expert predictions using grouped folds among Phase 5 training engines only; no OOF fold splits a single engine between fit and OOF prediction.
- Fits the adaptive gate on OOF absolute errors only, with each engine given equal total sample weight.
- Uses Phase 5 held-out validation engines only for comparison/reporting, not expert fitting or gate fitting.
- Does not load NASA test files or official test RUL labels.
- `engine_id`, `cycle`, and target `RUL` are excluded from gate inputs. Cycle is used only as an ordering/join key.

## Limits / research status

- This is an adaptive-ensemble candidate, not a verified novel research contribution.
- The Phase 5 validation labels are the 125-capped labels; Phase 1's target-cap decision and literature protocol still need final confirmation.
- Validation uses all cycle rows for held-out engines, so longer engine trajectories have more influence on row-weighted metrics. Engine-macro metrics are also reported to expose this.
- Baseline experts are trained with the fixed Phase 5 configuration. This phase does not conduct hyperparameter tuning or claim paper reproduction.
- Before publication claims, review closest full-text studies and run ablations/sensitivity analyses, including capped vs uncapped target behavior.
