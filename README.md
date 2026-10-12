# DARE-RUL

**DARE-RUL** (Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction) is a research project using NASA C-MAPSS FD001–FD004.

## Pipeline
0. Environment and Git setup
1. Dataset verification and research protocol
2. Kafka telemetry ingestion
3. Spark Structured Streaming and HDFS/Parquet
4. Multi-resolution temporal features
5. Literature baseline reproduction
6. Proposed adaptive ensemble
7. Accuracy, robustness, ablation, scalability and explainability
8. Maintenance decision support and demo

## Current verified milestones
- Phase 0: local environment checks passed; Python 3.10.11, Git, Docker/Compose, Java 11, WSL2.
- Dataset structure: FD001–FD004 passed initial validation; raw files remain local and are excluded from Git.
- Phase 2: 8/8 dataset/split ingestion smoke tests passed (500 events each).
- Phase 3: one 500-event FD001/train topic passed Spark 3.5.1/HDFS processing; 500 valid rows, zero invalid rows, duplicates and ordering warnings; five event-validation unit tests passed.
- Phase 4: Multi-resolution temporal features generated for FD001–FD004 with 15-cycle and 30-cycle windows; five unit tests and output read-back validation passed. Predictive accuracy and distributed scalability remain unevaluated.

## Important limitations
The Phase 2 test matrix is an ingestion smoke test, not a scalability benchmark. Phase 3 is one local Spark worker and one HDFS DataNode; it is not a distributed scaling/failure-recovery study. The Phase 1 research protocol still requires final review of the closest literature, baseline choices, RUL target cap and split/metric protocol.

## Repository guide
- `docs/project/architecture/phase_map.md`: system phases
- `docs/project/data_validation_summary.md`: dataset check
- `docs/project/phase1_checklist.md` and `phase1_exit_criteria.md`: Phase 0–1 state
- `docs/project/literature/`: literature matrix, research gap and evaluation protocol
- `docs/project/phase2_scope.md`, `phase2_event_schema.json`, `phase2_matrix_test.md`, `phase2_matrix_results.csv`, `phase2_run_summary.md`: Kafka design and evidence
- `docs/project/phase3_scope.md`, `phase3_runbook.md`, `phase3_run_summary.md`: Spark/HDFS design, operation and evidence
- `docs/project/research_log.md`: decisions, limitations and experiment register

Raw data, virtual environments, generated models, logs and experiment result files are intentionally kept out of GitHub. Commit only code, configs and curated summaries.
