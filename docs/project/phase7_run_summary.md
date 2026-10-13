# Phase 7 Run Summary — Ablation, Robustness, Explainability and Inference Scaling

- **Status:** PASS (all analysis outputs generated)
- **RUL cap:** 125 cycles (provisional; Phase 1 protocol decision remains open)
- **Seed:** 42
- **Official test RUL files:** not loaded or used.
- **Main feature addition:** 84 cross-window sensor features (21 sensors × 4 contrasts) derived from causal 15/30-cycle statistics.
- **New gate variants:** multi-resolution context; multi-resolution plus cross-window engineered contrasts; enhanced context without explicit disagreement summaries.
- **Interpretation guardrail:** Phase 7 uses the existing Phase 5/6 validation engines for exploratory ablations. Do not present these results as an independent final test.

## Best validation RMSE per subset

| Subset | Best method on this validation split | RMSE | MAE | Engine-macro MAE |
|---|---|---:|---:|---:|
| FD001 | cross_window_no_disagreement | 14.854 | 10.564 | 10.745 |
| FD002 | cross_window_error_gate | 19.346 | 14.253 | 14.677 |
| FD003 | cross_window_error_gate | 13.644 | 8.954 | 9.991 |
| FD004 | cross_window_no_disagreement | 19.683 | 13.938 | 14.755 |

## Feature-ablation methods

The combined metrics CSV includes the seven Phase 6 methods and three Phase 7 gates. Compare `multires_error_gate`, `cross_window_error_gate`, and `cross_window_no_disagreement` with `adaptive_error_gate`, `equal_average`, and the single experts. Lower errors are better; do not infer a universal win from one subset or metric.

## Paired engine bootstrap

`paired_bootstrap.csv` reports the cross-window gate minus selected comparators for engine-macro metrics. Negative differences favour the cross-window gate. Confidence intervals are conditional on this fixed validation cohort and are not an external test result.

## Sensor-feature noise stress test

`noise_robustness.csv` perturbs sensor-derived input feature columns by 1% and 5% of training-feature standard deviations at inference. This is a synthetic feature perturbation, not a validated physical sensor-fault model.

## Group-permutation explainability

`feature_group_importance.csv` measures how much validation performance changes when each input group is permuted. Positive deltas mean the score worsened after permutation, suggesting the group contributes useful signal on this validation split. This is a post-hoc diagnostic, not causal evidence.

## Inference benchmark

`inference_benchmark.csv` times local in-process gate inference for 1×, 2× and 5× repeated validation rows. It is a CPU inference microbenchmark only; it does not demonstrate distributed Spark/Kafka/HDFS throughput or fault recovery.

## Remaining limitations

- This run does not load official test labels.
- The validation set has already informed Phase 5/6 model comparison and is reused for Phase 7 exploratory ablations; do not continue tuning against it indefinitely.
- RUL cap 125 remains provisional until Phase 1 literature review and protocol approval are complete.
- Novelty, superiority, distributed scalability and real-aircraft generalization are not established by a successful run.

Generated files are local/ignored under `results/phase7/`; fitted gates are under `models/phase7/`.
