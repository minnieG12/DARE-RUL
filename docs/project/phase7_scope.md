# Phase 7 Scope — Ablation, Robustness, Explainability and Inference Scaling

## Goal

Stress-test the Phase 6 adaptive ensemble candidate, expand its gate context with multi-resolution information, quantify feature-group influence, and report uncertainty and local inference throughput without touching the official C-MAPSS test labels.

## Additional gate features

Phase 6 gate context used 30-cycle settings/sensor summaries and the four expert predictions/disagreement. Phase 7 adds:

- Both 15-cycle and 30-cycle summaries.
- Per-sensor short-vs-long rolling mean contrast.
- Per-sensor short-vs-long rolling standard-deviation ratio.
- Per-sensor short-vs-long rolling delta contrast.
- Per-sensor current reading standardized against its 30-cycle mean/std.

This adds 84 derived features (21 sensors × 4). These are calculated only from existing current/past rolling features; no engine ID, cycle number, RUL target, or future-cycle information is passed into the gate.

## Experiments

1. Feature ablation: compare Phase 6 methods against three Phase 7 gates (multi-resolution; multi-resolution plus engineered cross-window features; cross-window gate without explicit disagreement summaries).
2. Robustness: perturb sensor-derived feature inputs by 1% and 5% of training-feature standard deviation during gate inference.
3. Paired engine bootstrap: estimate confidence intervals for engine-macro error differences between cross-window gate and selected comparators.
4. Group-permutation explanation: measure score changes when context/prediction feature groups are permuted.
5. Inference benchmark: time 1×, 2× and 5× repeated validation rows through the gate models locally.
6. Kafka/Spark/HDFS replay/drain benchmark: send 500, 5,000 and 20,000 target-free events to unique topics and record valid HDFS counts and elapsed throughput.

## Leakage controls

- Uses Phase 5's existing engine split.
- Fits new error gates only on saved cross-fitted Phase 6 OOF predictions from Phase 5 training engines.
- The Phase 5 validation engines are used for ablation, robustness diagnostics, bootstrap and explainability; no gate is fitted on validation rows.
- Official test files and official test RUL target files are never opened.
- `engine_id`, `cycle`, `RUL` and `RUL_true_capped` are excluded from gate input features.

## Limitations

- Results are exploratory on the existing Phase 5 validation cohort. Repeatedly changing features in response to these results can overfit the validation set.
- The target cap of 125 is provisional pending the Phase 1 literature/protocol decision.
- The local inference microbenchmark is not evidence of distributed Spark/Kafka/HDFS scalability. The separate replay/drain benchmark characterizes the existing single-worker/single-DataNode setup only and is not a crash-recovery test.
- Positive ablation results do not establish novelty or generalization to real aircraft.
