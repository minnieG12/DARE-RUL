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

## Phase 2 record
- Initial shared-topic smoke test had an offset ambiguity; it was not used as the sole proof of end-to-end correctness.
- Expanded matrix then passed 8/8 isolated dataset/split scenarios (FD001–FD004, train/test), 500 messages per scenario; 4,000 delivered and validated, zero ordering warnings.
- See `phase2_matrix_results.csv` and `phase2_run_summary.md`.
- These are ingestion smoke tests, not the Phase 7 scalability benchmark.

## Phase 3 record
- Spark 3.5.1 and the Kafka connector started successfully after configuring a writable Ivy cache under `/tmp/dare-rul-ivy`.
- HDFS project directories were prepared for the Spark user using the corrected Hadoop CLI syntax.
- Run: `fd001_train_hdfsfix_20261013_031145`.
- Topic: `cmapss-p2-fd001-train-20261012150514886`.
- Expected 500; read back 500 valid Parquet rows; invalid rows 0; duplicate engine-cycle pairs 0; ordering warnings 0.
- Reported job runtime: 34.34 seconds. First-run dependency download was included, so this is not a steady-state benchmark.
- HDFS Parquet and both query checkpoint paths were listed; 5 event-validation tests passed.
- See `phase3_run_summary.md` and `phase3_runbook.md`.
- Phase 3 demonstrates a local integration only (one Spark worker, one HDFS DataNode). Scalability/recovery testing is still pending.


## Phase 4 record
- Offline multi-resolution features generated for FD001–FD004.
- Windows: 15 and 30 cycles.
- Five unit tests passed; output-integrity validation passed.
- Generated totals: 160,359 training rows, 104,897 test-trajectory rows, and 707 final test rows with 707 separate targets.
- Generated feature data remains local and excluded from Git.
- This milestone validates offline feature generation, not predictive accuracy, research novelty, or distributed scalability.
- Phase 1 research decisions on the RUL cap, validation split, metrics and baselines remain open.

## Phase 5 record
- Completed 16 baseline fits: RF15, HGB15, RF30 and HGB30 across FD001–FD004.
- Six Phase 5 unit tests passed.
- Validation split: 80/20 by engine, random seed 42.
- RUL cap used: 125 cycles; this remains provisional pending literature review and protocol approval.
- Predictors excluded `engine_id` and `cycle`.
- Metrics: RMSE, MAE and PHM08/NASA asymmetric score.
- Official test RUL files were not loaded.
- HGB30 achieved the lowest validation RMSE on FD001, FD002 and FD004; RF30 achieved the lowest on FD003.
- The 30-cycle window achieved lower RMSE than the corresponding 15-cycle window for both model types on all four subsets.
- Complete results: `phase5_run_summary.md`. Local metrics and prediction files are under `results/phase5/`; trained models are under `models/phase5/`.
- This is an internal validation baseline, not an official test evaluation, exact reproduction of a published paper, or proof of research novelty.
- The final target cap and evaluation protocol remain provisional pending literature review and mentor/team confirmation.

## Phase 6 record
- The complete OOF-calibrated adaptive ensemble run passed across FD001–FD004.
- Ten Phase 6 unit tests passed.
- Four-fold engine-grouped OOF predictions were generated for RF15, HGB15, RF30 and HGB30.
- Compared individual experts, equal averaging, static OOF-reliability weighting and adaptive error gating.
- Verified 28 validation metric rows, 217,196 combined prediction rows and 16 fitted error gates.
- Official NASA test RUL files were not loaded.
- Adaptive performance: lowest row-weighted RMSE on FD002, FD003 and FD004; HGB30 remained best on FD001. The NASA score results were not uniformly best for the adaptive gate.
- Results: `docs/project/phase6_run_summary.md`.
- The adaptive gate remains a candidate approach, not a proven novel contribution.
- Phase 1 literature review, target-cap sensitivity and final evaluation-protocol decisions remain open.
