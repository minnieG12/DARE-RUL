# DARE-RUL: how the dataset and test data are used

This document distinguishes the benchmark's training data, the official held-out test data, and the previously reused validation cohort.

## 1. NASA C-MAPSS files

- `train_FD001.txt` through `train_FD004.txt`: labeled engine-cycle histories used for feature construction and model training/validation.
- `test_FD001.txt` through `test_FD004.txt`: held-out engine histories that stop before failure. Sensor/operating-condition rows are model inputs; they do not contain the final remaining-life target per engine.
- `RUL_FD001.txt` through `RUL_FD004.txt`: official remaining-useful-life labels associated with the final rows of the matching test subset. These labels are for final scoring, not model fitting.
- `test_FD00*.txt` and `RUL_FD00*.txt` are paired by subset and the test engine ordering defined by the dataset protocol.

## 2. How this project uses them

| Stage | Data used | Allowed use |
|---|---|---|
| Phase 4 features | Train and test sensor/operating-condition histories | Compute past/current-cycle features separately per engine. No official test RUL targets are features. |
| Phase 5 baselines | Training engines split at engine level | Fit experts and compare candidate settings on the training-derived validation split. |
| Phase 6 ensemble | Training-only out-of-fold expert predictions and residuals | Calibrate reliability/gating from OOF evidence. Keep held engines out of corresponding expert fitting. |
| Phase 7 experiments | Training/validation evidence plus synthetic perturbations and replay workloads | Ablation, robustness, explainability and engineering benchmark. Synthetic noise is not a replacement for real sensor-fault validation. |
| Phase 8 inference | Official test sensor histories + frozen model/gate artifacts | Produce `results/phase8/test_predictions.csv` before loading the official target labels for scoring. |
| Phase 8 scoring | Official `RUL_FD00*.txt` labels paired to each test engine | Calculate the saved RMSE, MAE and NASA/PHM08 score in `test_scored_predictions.csv` and `final_test_metrics.csv`. This is the first documented official-label scoring step. |
| Phase 9 parity | Saved models/features and sampled test-engine predictors; compare rebuilt prediction to saved Phase 8 prediction | Verify inference reproduction. Parity is an engineering check, not model selection. |
| Phase 9 V2 experiment | Existing Phase 6 held-out validation cohort, already used in earlier comparisons | Exploratory comparison only. Metadata says no Phase 8 official test labels were read. It is not a fresh independent estimate. |
| Dashboard metrics view | Saved Phase 8 prediction/scored metric files | Display known scored results for analysis. Do not use the page to tune models against the same cohort. |
| SHAP view | Model input features with saved artifacts/canonical prediction function and a bounded background sample | Explain the function's output. Do not include target columns, engine ID or cycle index as model explanation features. Attributions are not causal effects. |

## 3. What the Phase 8 official test data means

The official test set is a held-out benchmark. The terminal logs state that the prediction-only CSV was written before official test targets were read for scoring. The saved evaluation includes:

- `test_predictions.csv`: prediction-only output
- `test_scored_predictions.csv`: predictions paired with true RUL for scoring/reporting
- `final_test_metrics.csv`: metrics for FD001–FD004
- `oof_fold_audit.csv`: training-fold provenance for the ensemble/gating evaluation
- `run_metadata.json`: run configuration/status metadata

Previously recorded counts were 707 prediction rows, 707 scored rows, 4 subset metric rows and 20 OOF audit rows.

## 4. What must not happen

- Do not use `RUL_FD00*.txt` to fit the experts or train the adaptive gate.
- Do not repeatedly tune V2, thresholds, feature sets or the gate after inspecting official test scores and still describe those scores as untouched.
- Do not present the old Phase 8 test metrics as a fresh test of the new V2 method.
- Do not claim prior protocol approval because the command-line `-ProtocolApproved` flag or a metadata Boolean was set. Use a real dated decision record; otherwise call Phase 8 scores exploratory.
- Do not report the recorded `443454.516` seconds as model runtime until its timer definition is verified; it is about 5.13 days.

## 5. Recommended report wording

“Models were fit and selected using training-derived, engine-grouped validation evidence. The official C-MAPSS test histories were used for inference, and the paired official RUL labels were used to compute a frozen set of final benchmark metrics. These historical scores were not used to tune later variants. The Phase 9 V2 comparison reused a prior validation cohort and is reported as exploratory.”
