# Phase 6 Run Summary — OOF-Calibrated Adaptive Ensemble

- **Status:** PASS (adaptive ensemble fit and compared on Phase 5 validation engines)
- **RUL cap:** 125 cycles (provisional, inherited from Phase 5)
- **OOF folds:** 4, grouped by engine on Phase 5 training engines only
- **Seed:** 42
- **Experts:** RF15, HGB15, RF30 and HGB30; expert hyperparameters follow Phase 5.
- **Ensemble comparators:** four individual experts, equal average, OOF engine-macro-MAE inverse-error weights, and adaptive per-row error gate.
- **Adaptive gate:** estimates each expert's absolute error using OOF-only examples, context features and expert disagreement; converts predicted errors into per-row inverse-error weights.
- **Official test RUL labels:** not read or used.

## Validation results

All metrics below use the same Phase 5 held-out validation engines and capped labels. Row-weighted metrics match Phase 5's evaluation unit. Engine-macro metrics average each engine equally, which helps reveal the effect of different trajectory lengths. Lower is better for all listed metrics.

| Subset | Method | Type | Rows | Engines | RMSE | MAE | NASA score sum | NASA score mean | Engine-macro RMSE | Engine-macro MAE | Engine-macro NASA mean |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FD001 | RF15 | individual_expert | 4070 | 20 | 16.657 | 11.984 | 26360.238 | 6.476717 | 15.691 | 12.186 | 6.683482 |
| FD001 | HGB15 | individual_expert | 4070 | 20 | 16.115 | 11.518 | 24706.424 | 6.070375 | 15.434 | 11.724 | 6.300861 |
| FD001 | RF30 | individual_expert | 4070 | 20 | 15.561 | 11.043 | 22191.537 | 5.452466 | 14.891 | 11.280 | 5.753784 |
| FD001 | HGB30 | individual_expert | 4070 | 20 | 14.919 | 10.496 | 18384.992 | 4.517197 | 14.339 | 10.655 | 4.701705 |
| FD001 | equal_average | fixed_ensemble | 4070 | 20 | 15.058 | 10.848 | 18918.340 | 4.648241 | 14.303 | 11.033 | 4.848502 |
| FD001 | oof_inverse_mae | fixed_ensemble_train_only_weights | 4070 | 20 | 15.026 | 10.819 | 18811.403 | 4.621966 | 14.277 | 11.004 | 4.821928 |
| FD001 | adaptive_error_gate | adaptive_ensemble_candidate | 4070 | 20 | 14.941 | 10.643 | 18851.492 | 4.631816 | 14.186 | 10.824 | 4.835776 |
| FD002 | RF15 | individual_expert | 10295 | 52 | 19.786 | 14.720 | 164536.952 | 15.982220 | 19.296 | 15.184 | 18.475789 |
| FD002 | HGB15 | individual_expert | 10295 | 52 | 19.712 | 14.418 | 155265.589 | 15.081650 | 19.183 | 14.840 | 17.376071 |
| FD002 | RF30 | individual_expert | 10295 | 52 | 19.592 | 14.688 | 149981.539 | 14.568387 | 19.135 | 15.137 | 16.753596 |
| FD002 | HGB30 | individual_expert | 10295 | 52 | 19.500 | 14.294 | 147231.489 | 14.301262 | 18.996 | 14.684 | 16.419086 |
| FD002 | equal_average | fixed_ensemble | 10295 | 52 | 19.380 | 14.393 | 143696.436 | 13.957886 | 18.853 | 14.819 | 16.059010 |
| FD002 | oof_inverse_mae | fixed_ensemble_train_only_weights | 10295 | 52 | 19.379 | 14.390 | 143638.748 | 13.952282 | 18.852 | 14.816 | 16.052111 |
| FD002 | adaptive_error_gate | adaptive_ensemble_candidate | 10295 | 52 | 19.353 | 14.267 | 144617.500 | 14.047353 | 18.814 | 14.693 | 16.170489 |
| FD003 | RF15 | individual_expert | 4708 | 20 | 15.319 | 10.378 | 31350.658 | 6.659018 | 15.201 | 11.416 | 7.801849 |
| FD003 | HGB15 | individual_expert | 4708 | 20 | 15.212 | 10.126 | 33284.270 | 7.069726 | 15.112 | 11.117 | 8.238849 |
| FD003 | RF30 | individual_expert | 4708 | 20 | 13.889 | 9.050 | 20126.136 | 4.274880 | 13.828 | 10.163 | 5.114433 |
| FD003 | HGB30 | individual_expert | 4708 | 20 | 14.039 | 9.030 | 20179.600 | 4.286236 | 14.016 | 10.100 | 5.075544 |
| FD003 | equal_average | fixed_ensemble | 4708 | 20 | 13.902 | 9.287 | 20711.708 | 4.399258 | 13.782 | 10.317 | 5.185271 |
| FD003 | oof_inverse_mae | fixed_ensemble_train_only_weights | 4708 | 20 | 13.858 | 9.243 | 20419.449 | 4.337181 | 13.741 | 10.276 | 5.115425 |
| FD003 | adaptive_error_gate | adaptive_ensemble_candidate | 4708 | 20 | 13.667 | 8.982 | 19999.384 | 4.247958 | 13.514 | 10.021 | 5.015683 |
| FD004 | RF15 | individual_expert | 11955 | 50 | 20.026 | 14.286 | 178469.017 | 14.928400 | 19.313 | 15.131 | 19.201286 |
| FD004 | HGB15 | individual_expert | 11955 | 50 | 20.052 | 14.194 | 190824.219 | 15.961875 | 19.378 | 15.033 | 20.678953 |
| FD004 | RF30 | individual_expert | 11955 | 50 | 19.929 | 14.308 | 170762.146 | 14.283743 | 19.234 | 15.113 | 18.365885 |
| FD004 | HGB30 | individual_expert | 11955 | 50 | 19.861 | 14.055 | 174554.227 | 14.600939 | 19.193 | 14.835 | 18.808412 |
| FD004 | equal_average | fixed_ensemble | 11955 | 50 | 19.702 | 14.064 | 168900.426 | 14.128016 | 18.955 | 14.882 | 18.214267 |
| FD004 | oof_inverse_mae | fixed_ensemble_train_only_weights | 11955 | 50 | 19.702 | 14.063 | 168911.424 | 14.128935 | 18.955 | 14.881 | 18.215562 |
| FD004 | adaptive_error_gate | adaptive_ensemble_candidate | 11955 | 50 | 19.686 | 13.950 | 169943.056 | 14.215228 | 18.917 | 14.769 | 18.325238 |

## Training-only OOF reliability

These engine-macro MAEs were calculated from cross-fitted predictions on Phase 5 training engines. They set static blend weights; the official test set was not involved.

| Subset | Expert | OOF engine-macro MAE | Static weight |
|---|---|---:|---:|
| FD001 | HGB15 | 13.948 | 0.2460 |
| FD001 | HGB30 | 12.896 | 0.2653 |
| FD001 | RF15 | 14.581 | 0.2356 |
| FD001 | RF30 | 13.541 | 0.2531 |
| FD002 | HGB15 | 15.249 | 0.2520 |
| FD002 | HGB30 | 15.069 | 0.2549 |
| FD002 | RF15 | 15.594 | 0.2466 |
| FD002 | RF30 | 15.600 | 0.2465 |
| FD003 | HGB15 | 11.951 | 0.2360 |
| FD003 | HGB30 | 10.379 | 0.2701 |
| FD003 | RF15 | 12.260 | 0.2302 |
| FD003 | RF30 | 10.639 | 0.2637 |
| FD004 | HGB15 | 12.946 | 0.2507 |
| FD004 | HGB30 | 12.930 | 0.2510 |
| FD004 | RF15 | 13.031 | 0.2491 |
| FD004 | RF30 | 13.023 | 0.2492 |

## Interpretation and limitations

- The adaptive gate is a candidate method, not a proven novel contribution. Its benefit must be judged against the individual experts and simple averaging on unseen engines.
- The validation engines were not used for OOF expert or gate fitting; validation data were used only for comparison/reporting.
- The gate's error targets are OOF absolute errors and its sample weights balance each engine during fitting.
- Validation rows from an engine are correlated. Row-weighted scores are provided for Phase 5 comparability; engine-macro scores are reported alongside them.
- Results are internal validation results, not official held-out test metrics and not evidence of distributed scalability.
- Phase 1 literature review and protocol approval (including capped vs uncapped sensitivity) remain prerequisites for publication claims.
Machine-readable artifacts are local/ignored under `results/phase6/`; gate models are under `models/phase6/`.


### Main findings

- The adaptive error gate achieved the lowest row-weighted validation RMSE on FD002, FD003 and FD004. HGB30 remained best on FD001.
- The adaptive gate achieved the lowest row-weighted MAE on FD002, FD003 and FD004. HGB30 remained best on FD001.
- The adaptive gate achieved the lowest engine-macro RMSE across all four subsets, meaning it performed well when each engine was weighted equally.
- The NASA asymmetric score did not consistently favour the adaptive gate. Static OOF-reliability weighting performed better on FD002, and equal averaging performed better on FD004.
- Improvements over simple averaging were small on FD002 and FD004. Additional sensitivity testing is necessary before making broad performance claims.
- These are results from one fixed engine-separated validation split. The official NASA test set has not been evaluated.