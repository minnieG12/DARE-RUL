# DARE-RUL Research and Experiment Log

## Project details
- Project: DARE-RUL — Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction
- Dataset: NASA C-MAPSS FD001–FD004
- Team / mentor: fill in
- Start date: 2026-10

## Research question (draft)
Can a multi-resolution ensemble of classical ML models, combined using validation-learned reliability and prediction-disagreement signals, improve C-MAPSS RUL estimates over comparable single models and fixed-weight ensembles, while being served by a measurable distributed ingestion/processing pipeline?

## Baseline protocol (not yet finalized)
- Dataset subset(s):
- RUL labeling and cap protocol:
- Train/validation split method:
- Features and preprocessing:
- Baseline model configurations:
- Metrics: RMSE, MAE, NASA score (if protocol-aligned)
- Random seeds / repeated runs:

## Proposed method (hypothesis, not a proven novelty claim)
1. Build 15-cycle and 30-cycle feature views without using future observations.
2. Train comparable Random Forest and Gradient Boosting experts on those views.
3. Estimate expert reliability using training/validation data only.
4. Derive a disagreement signal from expert predictions.
5. Compare a bounded adaptive combiner against fixed averaging and individual experts.
6. Freeze choices before evaluating on held-out test labels.

## Experiment register

| ID | Dataset | Features | Method | Config / seed | RMSE | MAE | NASA score | Runtime / latency | Notes |
|---|---|---|---|---|---:|---:|---:|---:|---|
| EXP-001 | | | | | | | | | |

## Phase 0–1 record
- Environment checks and dataset structural validation passed.
- All 12 C-MAPSS train/test/RUL files passed the initial structural validation; SHA-256 manifest generated.
- A 29-record literature matrix was seeded for review; full-text review, final baseline and mentor/team protocol confirmation remain open.
- Candidate models: RF-15, GB-15, RF-30 and GB-30.
- Comparators: individual experts, uniform averaging, validation-error weighting and standard stacking.
- Candidate gate signals: degradation context, validation-only expert reliability and prediction disagreement.
- Proposed contribution remains provisional pending the closest-paper comparison.
- Use engine-separated validation; keep held-out test labels out of model/gate selection.
- Confirm training RUL cap, preprocessing and scoring protocol before final experiments.

## Phase 2 record — 2026-10-12
- Initial shared-topic smoke test had an offset ambiguity; it was not used as the sole proof of end-to-end correctness.
- Expanded matrix then passed 8/8 isolated dataset/split scenarios (FD001–FD004, train/test), 500 messages per scenario; 4,000 delivered and validated, zero ordering warnings.
- See `phase2_matrix_results.csv` and `phase2_run_summary.md`.
- These are ingestion smoke tests, not the Phase 7 scalability benchmark.

## Phase 3 record — 2026-10-13
- Spark 3.5.1 and the Kafka connector started successfully after configuring a writable Ivy cache under `/tmp/dare-rul-ivy`.
- HDFS project directories were prepared for the Spark user using the corrected Hadoop CLI syntax.
- Run: `fd001_train_hdfsfix_20261013_031145`.
- Topic: `cmapss-p2-fd001-train-20261012150514886`.
- Expected 500; read back 500 valid Parquet rows; invalid rows 0; duplicate engine-cycle pairs 0; ordering warnings 0.
- Reported job runtime: 34.34 seconds. First-run dependency download was included, so this is not a steady-state benchmark.
- HDFS Parquet and both query checkpoint paths were listed; 5 event-validation tests passed.
- See `phase3_run_summary.md` and `phase3_runbook.md`.
- Phase 3 demonstrates a local integration only (one Spark worker, one HDFS DataNode). Scalability/recovery testing is still pending.


## Phase 4 record — 2026-10-13
- Offline multi-resolution features generated for FD001–FD004.
- Windows: 15 and 30 cycles.
- Five unit tests passed; output-integrity validation passed.
- Generated totals: 160,359 training rows, 104,897 test-trajectory rows, and 707 final test rows with 707 separate targets.
- Generated feature data remains local and excluded from Git.
- This milestone validates offline feature generation, not predictive accuracy, research novelty, or distributed scalability.
- Phase 1 research decisions on the RUL cap, validation split, metrics and baselines remain open.
