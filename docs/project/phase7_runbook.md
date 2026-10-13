# Phase 7 Runbook

## Prerequisites

- Phases 4, 5 and 6 completed locally.
- `data/features/phase4/FD001` through `FD004` exist.
- `models/phase5/<subset>/RF15_metadata.json` exists.
- `results/phase5/validation_predictions.csv` exists.
- `results/phase6/<subset>/oof_predictions.csv`, `results/phase6/validation_metrics.csv` and `results/phase6/validation_predictions.csv` exist.
- `.venv` includes NumPy, pandas, PyArrow, scikit-learn, joblib and pytest.

## Run

From the project root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_phase7_experiments.py -q
.\scripts\phase7\run_phase7.ps1
```

Do not run multiple copies in parallel. This phase reuses the expensive Phase 6 OOF predictions; it does not retrain the Random Forest/HistGradientBoosting experts, only the small error-gate models.

## Local outputs (should stay ignored)

- `results/phase7/validation_metrics.csv` — 40 total methods (7 Phase 6 methods + 3 new gates, across four subsets).
- `results/phase7/validation_predictions.csv` — Phase 6 and new gate predictions.
- `results/phase7/feature_ablation.csv` — key individual/ensemble feature comparisons.
- `results/phase7/noise_robustness.csv` — 0%, 1% and 5% feature perturbation checks.
- `results/phase7/paired_bootstrap.csv` — paired engine bootstrap intervals.
- `results/phase7/feature_group_importance.csv` — grouped permutation influence estimates.
- `results/phase7/inference_benchmark.csv` — local in-process timing.
- `results/phase7/run_metadata.json` — reproducibility/leakage metadata.
- `models/phase7/<subset>/gate_*.joblib` — fitted gate models.
- `docs/project/phase7_run_summary.md` — generated readable summary.

## Success criteria

- Phase 7 tests pass.
- Script reports `PHASE 7 EXPERIMENT PASS`.
- `validation_metrics.csv` has 40 rows, 10 methods per subset.
- Combined predictions contain finite targets/predictions.
- Metadata has `official_test_targets_used: false`.
- Output tables for ablation, robustness, bootstrap, feature-group permutation and inference timing exist.

## Interpretation

This is an exploratory validation and diagnostic phase using the existing Phase 5 validation engines. Do not treat it as final generalization evidence or official benchmark evaluation. Freeze methods after this phase; preserve official test labels for later final evaluation.

## Run the Kafka → Spark → HDFS replay/drain benchmark

This is the distributed-pipeline part of Phase 7. It checks whether the existing single-worker/single-DataNode setup can process 500, 5,000 and 20,000 target-free events end-to-end in controlled runs. The producer sends first and Spark drains the topic afterward, so this is a batch replay/drain benchmark, not simultaneous real-time ingestion.

1. Start the Phase 2 Kafka stack and verify the broker is reachable:

   ```powershell
   .\scripts\kafka\start_kafka.ps1
   ```

2. Start and verify the Phase 3 Spark/HDFS cluster:

   ```powershell
   .\scripts\phase3\start_phase3_cluster.ps1
   .\scripts\phase3\verify_phase3_cluster.ps1
   ```

3. Run the benchmark using FD001 train rows (the file contains enough records for all three default sizes):

   ```powershell
   .\scripts\phase7\benchmark_streaming.ps1
   ```

4. Review the recorded results:

   ```powershell
   Get-Content .\docs\project\phase7_streaming_benchmark_summary.md
   Import-Csv .\results\phase7\streaming_scalability_benchmark.csv | Format-Table requested_messages, valid_rows, spark_hdfs_elapsed_seconds, spark_hdfs_messages_per_second, status -AutoSize
   ```

Every scale run uses a unique Kafka topic and HDFS run label. Do not delete HDFS checkpoints or reuse a run label. Each run must have the requested row count, zero invalid rows, zero duplicate engine-cycle pairs, and zero cycle-order warnings.

**Limits:** this is one Spark worker and one HDFS DataNode, so it gives a baseline curve, not proof of horizontal scaling. The current Phase 3 job is not a crash-recovery test; this phase does not claim resume-after-kill semantics.
