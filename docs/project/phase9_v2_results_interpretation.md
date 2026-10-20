# Adaptive ensemble V2: validation interpretation

**Status: V2 did not improve the current Phase 6 adaptive gate on the recorded comparison. Keep V2 experimental.**

## Results recorded in the terminal run

The comparison used the existing Phase 6 held-out validation engines. That cohort had already been used for earlier comparisons, so the experiment is exploratory and should not be treated as a new independent estimate of model-selection performance.

| Subset | V1 RMSE | V2 RMSE | V2 − V1 RMSE | Paired engine-bootstrap 95% interval | V1 MAE | V2 MAE | V2 − V1 MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| FD001 | 14.9407 | 14.9547 | +0.01397 | [+0.00812, +0.02070] | 10.6426 | 10.6745 | +0.03195 |
| FD002 | 19.3529 | 19.3573 | +0.00441 | [+0.00199, +0.00691] | 14.2667 | 14.2912 | +0.02450 |
| FD003 | 13.6666 | 13.6991 | +0.03247 | [+0.01444, +0.05275] | 8.9819 | 9.0331 | +0.05121 |
| FD004 | 19.6863 | 19.6887 | +0.00246 | [−0.00026, +0.00561] | 13.9500 | 13.9726 | +0.02255 |

**How to read this:** lower RMSE and MAE are better. V2's error difference is positive on all four subsets, so V2 has higher error than V1 in this run. The paired engine-bootstrap interval is above zero for FD001–FD003; for FD004 it includes zero. These intervals describe resampling variability on this already reused cohort; they are not a clean, independent final generalization estimate.

V2's configuration used `error_floor=0.5`, `max_weight=0.65`, `shrinkage=0.20`, seed 42 and 500 bootstrap resamples. The run recorded zero fallback rows. Numerical guardrails passed, but that is different from improved predictive accuracy.

## What this means

- Do not promote V2 as the new best model based on this run.
- Preserve V1 and V2 as separate implementations. The bounded/shrunk version is useful as an ablation but did not improve RMSE or MAE here.
- V1 itself remains a **candidate**, not a validated final winner: the validation cohort has been reused, and the RUL-cap/research protocol still needs formal closure.
- Do not select new V2 parameters based on the already observed Phase 8 official test scores.

## Recommended improvement path

1. Stop tuning against this reused validation cohort. Keep the above result as a documented negative finding.
2. Build an outer engine-grouped validation plan using only the labeled training engines. Reserve each outer fold for scoring only.
3. Inside each outer-training fold, generate inner engine-grouped OOF predictions for RF15, HGB15, RF30 and HGB30. Fit the error gates and any static weights using only those inner OOF records.
4. Fit the expert models on the outer-training engines, and score the outer-held-out engines. Keep gate fitting, normalization and all parameter choice inside the outer-training fold.
5. Compare V1, V2, equal averaging, static OOF reliability weighting and the best single expert using RMSE, MAE, NASA score, engine-macro metrics and paired engine-block bootstrap intervals.
6. If tuning `shrinkage`, `max_weight` or `error_floor`, select them only within inner folds. Evaluate the selected configuration on outer folds once. Report all subsets and metrics; do not report only the best subset.
7. Keep V2 only if it offers repeatable benefit across outer folds or a documented robustness/interpretability advantage despite similar accuracy. Otherwise record it as a negative result and keep the simpler method.

The Phase 8 official test cohort has already been scored. It remains a frozen historical evaluation and must not be used to tune V2 or choose between methods.
