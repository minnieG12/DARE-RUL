# DARE-RUL Phase 7 Pack — Start Here

Phase 6 is complete as an engineering milestone. Phase 7 adds more information to the adaptive gate and tests it rather than assuming it is better.

## What's being added?

The Phase 6 gate used 30-cycle context plus expert predictions and disagreement. Phase 7 compares three new gate variants:

1. Both 15- and 30-cycle features.
2. Both windows plus 84 engineered cross-window sensor contrasts: short/long mean gap, variability ratio, short/long delta gap, and current-vs-long-window standardized value for each of 21 sensors.
3. The same enhanced sensor features and raw expert predictions, but without explicit disagreement summary features.

All derived features use current and past-only Phase 4 rolling statistics. The run does not load official test RUL labels.

## Where to start

1. Extract this ZIP in `E:\Projects\big data\DARE-RUL` after confirming the new file paths do not already exist.
2. Run `\.venv\Scripts\python.exe -m pytest .\tests\test_phase7_experiments.py -q`.
3. Run `\.\scripts\phase7\run_phase7.ps1`.
4. Review `docs\project\phase7_run_summary.md` and outputs under local/ignored `results\phase7`.
5. For the distributed-pipeline benchmark, start Kafka and Phase 3 Spark/HDFS, then run `\.\scripts\phase7\benchmark_streaming.ps1`. Read `docs\project\phase7_streaming_benchmark_summary.md`.
6. Complete the documentation and Git push steps given in the conversation.

## Output files

The ML analysis runner creates validation metric/prediction comparisons, feature ablation, paired engine bootstrap confidence intervals, sensor-feature noise stress results, group-permutation importance, inference timing, and metadata. The separate streaming script writes `results/phase7/streaming_scalability_benchmark.csv` plus a tracked Markdown summary.

## Correct interpretation

These feature variants and validation analyses are exploratory. If the new gate does not improve simple averaging consistently, report that. The Phase 5 validation engines have already been used for previous model comparisons, so official test evaluation must happen only after the Phase 1 target-cap/research protocol is frozen. The current distributed test is a controlled single-worker replay/drain test; it does not prove horizontal scaling or crash recovery.
