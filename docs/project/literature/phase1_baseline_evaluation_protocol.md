# Baseline and evaluation protocol — version 1

## Dataset and prediction target

- Dataset: NASA C-MAPSS `FD001`, `FD002`, `FD003`, `FD004` from `data/CMAPSSData`.
- Training sensor rows: 26 columns (engine ID, cycle, three operating settings, 21 sensor readings).
- For a training trajectory, raw RUL at a cycle is `last_training_cycle_for_engine - current_cycle`.
- Working label rule: clip training RUL at 125 cycles (`min(raw_RUL, 125)`) for the primary experiment. Record this choice in every run. Keep official `RUL_FD00x.txt` targets separate for evaluation at the last observed test cycle; report that the target rule differs from an uncapped training label by design. If time permits, run an uncapped sensitivity experiment.
- The Kafka payload must not include RUL/target fields.

## Split rules

1. Keep the official C-MAPSS test split untouched until final evaluation.
2. Split training **by engine ID**, not by random rows, to avoid rows from one engine appearing in both training and validation.
3. Fit any transformations, feature selection, expert-reliability statistics and gate weights using training folds only.
4. Use out-of-fold expert predictions for stacking/gate training. Freeze the method before using the official test RUL labels.

## Models to compare

- RF-15, GB-15, RF-30, GB-30.
- Uniform average of the four experts.
- Validation-error-weighted average (weights based on validation-only errors).
- Conventional stacking with an out-of-fold meta-model.
- Candidate DARE-RUL gate using available degradation context + validation-derived reliability + expert disagreement.

## Features

Create causal rolling features separately within each engine, in cycle order. Candidate windows are 15 and 30 cycles. Use rolling means and standard deviations, plus differences/trends for selected sensors. At cycle `t`, a feature may use rows at or before `t` only—never future cycles. First version should document treatment of early cycles with fewer than a full window (min-periods / missing-value policy) and apply the same rule in train and test.

## Metrics

Report all values per FD subset and do not show only a pooled average:
- RMSE (penalizes large errors more strongly).
- MAE (average error in cycles).
- NASA PHM08 asymmetric score using a documented sign convention; with `d = predicted_RUL - true_RUL`, use `exp(-d/13)-1` for `d < 0`, otherwise `exp(d/10)-1`, summed across engines. Verify this formula against the scoring reference before final publication.
- Expert disagreement (e.g. standard deviation/range), clearly labelled as a warning signal and **not calibrated uncertainty**.

## Ablations

Compare the full gate with variants removing: (a) the 30-cycle experts, (b) degradation-context inputs, (c) reliability inputs, (d) disagreement inputs. Include fixed averaging and standard stacking. Report negative results as well as improvements.

## Big Data metrics

Independently measure Kafka delivery success/errors, message order per key, events/second, consumer processing latency and resource use. When Spark/HDFS are wired in Phase 3, measure end-to-end latency, checkpoint/recovery behavior and Parquet output correctness. A single-machine Docker test is not proof of multi-node production scalability. Separate the original C-MAPSS replay rate from any duplicated/synthetic stress-load test.

## Baseline selection rationale

RF and Gradient Boosting provide transparent, reproducible classical ML experts that run quickly and are suitable for feature-based input. Static averaging, validation-error weighting and ordinary stacking are required comparators because published RUL studies already combine models and adapt ensemble weights. The proposed gate should only be retained as a contribution if controlled comparisons show meaningful value.
