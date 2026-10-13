# Phase 5 Baseline Interpretation and Closure Note

## Engineering milestone status

The Phase 5 implementation and baseline run are complete for the internal validation milestone.

Evidence from the local run transcript:

- Six unit tests passed.
- Sixteen model fits completed: RF15, HGB15, RF30 and HGB30 for FD001–FD004.
- Sixteen model artifacts and sixteen metric rows were verified.
- The 20% engine-separated validation split used seed 42.
- The run used a 125-cycle RUL cap.
- The script did not load the official test RUL files.
- Results and model artifacts remain local/ignored by Git.
- Commit `7d5a611` and tag `phase-5-complete` were pushed.

## Main observations

- HGB30 produced the lowest validation RMSE on FD001, FD002 and FD004; RF30 was lowest on FD003.
- The 30-cycle feature window produced lower validation RMSE than its matching 15-cycle version for both model families on all four subsets in this run.
- Random Forest took longer to fit than Histogram Gradient Boosting on this machine.
- MAE, RMSE and the asymmetric NASA score do not always rank models identically, so preserve all metrics.

## Limits

These are internal validation results across all cycle rows of held-out engines. They are not official C-MAPSS test scores and do not reproduce a published result or establish novelty. The 125-cycle cap and final evaluation protocol remain provisional until the closest literature is reviewed and the mentor/team confirms the choices.
