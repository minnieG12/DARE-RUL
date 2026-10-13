# Phase 5 Run Summary — Classical ML Baselines

- **Status:** PASS (baseline training and engine-separated validation completed)
- **RUL cap used for this run:** 125
- **Engine-separated validation fraction:** 20%
- **Random seed:** 42
- **Validation features:** operating settings, current sensor values and one selected temporal window; `engine_id` and `cycle` excluded.
- **Official test RUL labels:** not read or used in this phase.
- **Target cap note:** 125 is a common C-MAPSS benchmark convention; this run uses it as a provisional primary configuration. Complete close-paper review and protocol approval before publication claims.

## Validation results

Lower is better for RMSE, MAE and NASA score. Scores here are calculated across all cycle rows belonging to the held-out validation engines; longer trajectories therefore contribute more rows.

| Subset | Model | Window | Train engines | Validation engines | Validation rows | Features | RMSE | MAE | NASA score (sum) | NASA score (mean) | Fit seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FD001 | HGB30 | 30 | 80 | 20 | 4070 | 87 | 14.919 | 10.496 | 18384.992 | 4.517197 | 2.3 |
| FD001 | RF30 | 30 | 80 | 20 | 4070 | 87 | 15.561 | 11.043 | 22191.537 | 5.452466 | 15.0 |
| FD001 | HGB15 | 15 | 80 | 20 | 4070 | 87 | 16.115 | 11.518 | 24706.424 | 6.070375 | 2.2 |
| FD001 | RF15 | 15 | 80 | 20 | 4070 | 87 | 16.657 | 11.984 | 26360.238 | 6.476717 | 14.4 |
| FD002 | HGB30 | 30 | 208 | 52 | 10295 | 87 | 19.500 | 14.294 | 147231.489 | 14.301262 | 4.6 |
| FD002 | RF30 | 30 | 208 | 52 | 10295 | 87 | 19.592 | 14.688 | 149981.539 | 14.568387 | 93.0 |
| FD002 | HGB15 | 15 | 208 | 52 | 10295 | 87 | 19.712 | 14.418 | 155265.589 | 15.081650 | 3.7 |
| FD002 | RF15 | 15 | 208 | 52 | 10295 | 87 | 19.786 | 14.720 | 164536.952 | 15.982220 | 89.0 |
| FD003 | RF30 | 30 | 80 | 20 | 4708 | 87 | 13.889 | 9.050 | 20126.136 | 4.274880 | 24.4 |
| FD003 | HGB30 | 30 | 80 | 20 | 4708 | 87 | 14.039 | 9.030 | 20179.600 | 4.286236 | 2.1 |
| FD003 | HGB15 | 15 | 80 | 20 | 4708 | 87 | 15.212 | 10.126 | 33284.270 | 7.069726 | 2.2 |
| FD003 | RF15 | 15 | 80 | 20 | 4708 | 87 | 15.319 | 10.378 | 31350.658 | 6.659018 | 23.3 |
| FD004 | HGB30 | 30 | 199 | 50 | 11955 | 87 | 19.861 | 14.055 | 174554.227 | 14.600939 | 3.1 |
| FD004 | RF30 | 30 | 199 | 50 | 11955 | 87 | 19.929 | 14.308 | 170762.146 | 14.283743 | 109.7 |
| FD004 | RF15 | 15 | 199 | 50 | 11955 | 87 | 20.026 | 14.286 | 178469.017 | 14.928400 | 119.2 |
| FD004 | HGB15 | 15 | 199 | 50 | 11955 | 87 | 20.052 | 14.194 | 190824.219 | 15.961875 | 3.0 |

## Best validation RMSE per subset

| Subset | Best validation model | RMSE | MAE | NASA score (sum) |
|---|---|---:|---:|---:|
| FD001 | HGB30 | 14.919 | 10.496 | 18384.992 |
| FD002 | HGB30 | 19.500 | 14.294 | 147231.489 |
| FD003 | RF30 | 13.889 | 9.050 | 20126.136 |
| FD004 | HGB30 | 19.861 | 14.055 | 174554.227 |

## Interpretation and limits

- Validation engines are wholly separate from training engines; all models for a subset use the same split.
- Fixed baseline settings were used; this is not a hyperparameter search.
- This phase establishes internal validation baselines only. It does not evaluate official held-out test labels, prove superiority over published papers, or establish research novelty.
- The standard official test targets remain untouched for the later frozen evaluation protocol.
- The next steps are to review the nearest literature and protocol, then use these baselines as comparators for the Phase 6 adaptive ensemble.

Machine-readable metrics and prediction files are under `results/phase5/` (local/ignored); trained model artifacts are under `models/phase5/` (local/ignored).
