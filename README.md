# DARE-RUL

**DARE-RUL** (Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction) is a research prototype for estimating remaining useful life (RUL) on the NASA C-MAPSS FD001–FD004 simulated turbofan benchmark. It combines a Kafka → Spark Structured Streaming → HDFS/Parquet data path with multi-resolution temporal features, classical ML experts, adaptive ensemble experiments, and an interactive research dashboard.

## Pipeline overview

1. Environment and repository setup
2. Dataset verification and research protocol
3. Kafka telemetry ingestion
4. Spark Structured Streaming and HDFS/Parquet
5. Multi-resolution temporal features
6. Baseline models
7. Adaptive ensemble V1
8. Ablation and streaming benchmark
9. Frozen evaluation and maintenance demonstration
10. Adaptive ensemble V2, dashboard and SHAP exploration
11. Research closure and final acceptance

The phase names above are a navigation map; detailed milestones and their exit criteria are recorded in `docs/project/`.

## Current verified phase status

| Phase | Status | Evidence and remaining work |
|---|---|---|
| 0 — Environment and Git | PASS | Python 3.10.11 virtual environment, Git, Docker/Compose, Java and WSL2 checked. Finish only the final clean-repository and fresh-shell reproducibility review. |
| 1 — Dataset and research protocol | OPEN | Dataset files were structurally validated and a literature matrix exists. The close-paper review, research gap, cap sensitivity and final evaluation protocol still need closure. |
| 2 — Kafka ingestion | PASS | Eight FD001–FD004 × train/test smoke scenarios, 500 events each; 4,000 events validated. |
| 3 — Spark/HDFS | PASS WITH LOCAL CONFIGURATION FOLLOW-UP | 500-event Spark/HDFS integration/read-back passed. The current cluster has one Spark worker and one DataNode. An inspection found blocks requesting three replicas despite only one live replica; align the local profile or add DataNodes before making redundancy claims. |
| 4 — Temporal features | PASS | 15-cycle and 30-cycle feature views built; five feature tests passed and saved Parquet outputs are present. |
| 5 — Baselines | PASS — VALIDATION | RF15, HGB15, RF30 and HGB30 were compared across all four subsets with an engine-level validation split; 16 fits and six tests passed. The cap/protocol remains a research decision. |
| 6 — Adaptive ensemble V1 | PASS — CANDIDATE METHOD | Four-fold engine-grouped OOF reliability/error gating was compared with individual experts and fixed ensembles; ten tests passed. The method is not yet an established novel or universal winner. |
| 7 — Ablation and streaming benchmark | PASS — LOCAL BENCHMARK | Model-side analyses and 500/5,000/20,000-message replay/drain tests completed. Reported rows/s were 17.05, 84.25 and 131.78; each run had matching row counts and zero invalid, duplicate or cycle-order-warning records. |
| 8 — Frozen test evaluation | PASS — PUSHED/TAGGED | Commit `8d6401c`, tag `phase-8-complete`; 707 predictions and scores, four metric rows, 20 OOF audit rows, plus the maintenance demo. Protocol approval evidence remains unverified, so the scores must be treated as exploratory until reconciled. |
| 9 — V2, dashboard and SHAP | IMPLEMENTED; ACCEPTANCE IN PROGRESS | V2 comparison and Streamlit dashboard code are pushed; `phase-9-complete` exists at `8077c91`. The 53-test run passed and parity passed on one engine from each subset. The recorded V2 RMSE and MAE are slightly worse than V1 on all four subsets; the live SHAP calculation and current UI polish still need hands-on verification. |
| 10 — Research closure | OPEN | The intended literature/research documents have not been completed by the commands shown in the latest transcript; the attempted commit had no staged research changes. |
| 11 — Final acceptance | OPEN | A commit named `phase-11: complete final integration and acceptance checks` added only two planning documents. It did not, by itself, complete the end-to-end acceptance tests. |

## Research and evaluation boundaries

- Phase 8 official test scores are a frozen historical result. New model design choices must use training/validation evidence rather than repeated tuning on those scores.
- The recorded V2 validation run reuses the earlier Phase 6 validation cohort; it is exploratory rather than an independent selection estimate.
- The streaming throughput numbers are local replay/drain measurements, not proof of concurrent real-time operation, horizontal scaling or fault recovery.
- The dashboard is a research tool for exploring predictions and model explanations. Its priority bands are configurable demo categories, not operational maintenance instructions.

## Where to start

- `docs/project/research_log.md`: experiment history and open decisions.
- `docs/project/phase5_protocol.md` and `phase5_run_summary.md`: baseline setup and evidence.
- `docs/project/phase6_protocol.md` and `phase6_run_summary.md`: adaptive ensemble V1.
- `docs/project/phase7_streaming_benchmark_summary.md`: recorded replay/drain benchmark values.
- `docs/project/phase8_final_test_summary.md`: saved evaluation results and caveats.
- `docs/project/phase9_v2_results_interpretation.md`: V1 versus V2 interpretation and recommended next experiment.
- `docs/project/dashboard_ui_polish.md`: dashboard UI changes in the companion polish pack.

Raw datasets, virtual environments, trained models and generated experiment outputs remain local and should not be added to Git.
