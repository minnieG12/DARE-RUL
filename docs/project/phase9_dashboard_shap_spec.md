# Phase 9 — Adaptive Ensemble V2, Dashboard and SHAP

## Scope

This pack adds (1) a bounded/shrinkage-stabilized blend helper for validation experiments and (2) a Streamlit dashboard using existing Phase 8 outputs and saved model artifacts. It does not retrain or rescore the official Phase 8 test cohort.

## V2 combiner helper

`scripts/phase9/ensemble_v2.py` implements a testable combiner function with:

- four expert inputs: RF15, HGB15, RF30, HGB30;
- normalized OOF-derived static weights as the fallback prior;
- inverse expected-error weights with an error floor;
- shrinkage toward static weights;
- a maximum expert weight cap;
- static fallback for rows with non-finite expected-error estimates;
- rejection of non-finite expert predictions;
- final RUL clipping.

This is a candidate rule, not an automatically approved replacement. Tune/assess it only on engine-separated training/validation evidence. The Phase 8 official test cohort was already scored and is frozen. Do not select V2 hyperparameters on those scores.

## Dashboard

The dashboard reads `results/phase8` CSVs only for the overview/evaluation pages. It uses local `models/phase8`, `data/features/phase4` and the existing `scripts/phase7/phase7_core.py` only when the SHAP page is requested.

SHAP explanation uses `shap.PermutationExplainer` over the full saved expert + gate + combiner prediction function. It performs a prediction-parity check against the saved Phase 8 prediction for the chosen engine before rendering explanations. Identifier/target columns are not explainer inputs. Attribution is model explanation relative to a sampled training background; it is not causal evidence or aviation maintenance policy.

## Acceptance criteria

- V2 helper tests pass and are added to the full test suite.
- V2 validation report compares each expert, equal average, the existing V1 adaptive gate and V2 on identical engine-level validation rows; report row-weighted and engine-macro metrics, plus paired engine bootstrap uncertainty.
- The dashboard loads saved CSVs, supports subset/tier/search filters, displays plots and exports filtered rows.
- SHAP runs only after parity checks pass; missing artifacts/schema mismatches show a clear UI error.
- No V2 settings or model choices are made using Phase 8 official test scores.
