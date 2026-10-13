# Phase 7 Troubleshooting

## Missing Phase 4/5/6 files

Check that the previous phases were run successfully. Phase 7 requires local features, Phase 5 metadata/predictions, and Phase 6 OOF/validation predictions. It does not reconstruct missing upstream outputs automatically.

## Missing feature columns

Rebuild Phase 4 features using the committed Phase 4 script. The current Phase 7 code expects sensor columns like `sensor_1_w15_mean`, `sensor_1_w15_std`, `sensor_1_w15_delta`, and their 30-cycle equivalents.

## Metric row count is not 40

There should be 28 existing Phase 6 metrics and 12 new Phase 7 gate metrics. Confirm `results/phase6/validation_metrics.csv` contains 28 rows and all four subsets before rerunning.

## Unexpected validation alignment or target mismatch

Do not bypass the check. Confirm `models/phase5/<subset>/RF15_metadata.json`, Phase 5 validation predictions, Phase 4 train features and Phase 6 OOF files originate from the same split and RUL cap 125.

## Output files are being staged by Git

The generated models and results should be ignored. Check with `git check-ignore -v results/phase7/validation_metrics.csv` and `git check-ignore -v models/phase7/FD001/gate_cross_window_gate_RF15.joblib`. Never use `git add -f` for these artifacts.

## Warnings about scalability or noise

The inference benchmark is local CPU timing with repeated records, not distributed Spark/Kafka/HDFS benchmarking. The noise test perturbs precomputed sensor-derived features, not the physical raw-sensor stream. Keep those limitations in the report.


## Streaming benchmark fails to create a topic

Confirm the Phase 2 Kafka service is up and `docker\kafka\compose.yaml` exists. The benchmark creates a uniquely named topic for each size, so do not pre-create that same topic.

## Producer sends fewer messages than requested

The `--max-messages` value cannot exceed the raw input file's number of rows. The default 20,000-message test uses `FD001/train`, which contains enough rows. If using another subset/split, choose sizes no larger than the source file.

## Spark/HDFS summary not PASS

Stop the benchmark and inspect the corresponding `results/phase7/*_spark.log` and `results/phase3/<run_label>_summary.json`. Do not reuse the run label or delete checkpoints blindly. Use a new benchmark run so every run gets unique topics and HDFS paths.
