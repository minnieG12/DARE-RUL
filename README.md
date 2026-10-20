# DARE-RUL

**DARE-RUL** (Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction) is a research prototype for remaining useful life (RUL) estimation using NASA C-MAPSS FD001–FD004. It combines multi-resolution temporal features, classical machine-learning experts, an adaptive ensemble candidate, and a Kafka–Spark–HDFS telemetry pipeline.

> **Current research status:** Phases 0 and 2–8 have recorded implementation milestones. Phase 1 (research protocol and closest-related-work review) remains open. Phase 8 official test-cohort scoring has been executed, but prior protocol-approval evidence has not yet been independently verified; treat those scores as exploratory until that status is resolved. This is a research benchmark, not a validated aviation maintenance system.

## Project pipeline

| Phase | Name | Current status | Main evidence | Remaining work |
|---|---|---|---|---|
| 0 | Environment and repository setup | **PASS** | Python 3.10.11 virtual environment, Git, Docker/Compose, Java 11 and WSL2 checks recorded. | Keep setup instructions and ignore rules reproducible; finish repository hygiene at final acceptance. |
| 1 | Dataset verification and research protocol | **OPEN** | All 12 C-MAPSS train/test/RUL files were structurally checked and a SHA-256 manifest was generated; a preliminary literature matrix exists. | Complete the closest-paper review, research-gap statement, RUL-cap decision, split/metric protocol and any genuine mentor/team approval record. |
| 2 | Kafka telemetry ingestion | **PASS** | Eight isolated scenarios (FD001–FD004 × train/test), 500 events each; 4,000 events validated with zero ordering warnings. | Preserve repeatable commands and run evidence. |
| 3 | Spark Structured Streaming and HDFS/Parquet | **PASS — local integration** | One FD001 training replay produced 500 valid Parquet rows; no invalid or duplicate engine-cycle pairs or ordering warnings were reported. Five event-validation tests passed. | Document single-worker/single-DataNode limits; resolve the under-replication warning against configured HDFS replication. |
| 4 | Multi-resolution temporal features | **PASS** | 15- and 30-cycle feature views generated for all four subsets; 152 feature columns were reported; five tests and output read-back validation passed. | Keep the feature dictionary and future-information/leakage boundaries explicit. |
| 5 | Classical ML baselines | **PASS — validation only** | RF15, HGB15, RF30 and HGB30 fitted across FD001–FD004; 16 fits, engine-level 80/20 validation and six tests recorded. | Preserve configuration and validation results; reconcile historical provisional-protocol language after the research decision. |
| 6 | OOF-calibrated adaptive ensemble | **PASS — candidate method** | Four-fold engine-grouped OOF predictions used to compare individual experts, equal averaging, static reliability weighting and adaptive gating; ten tests recorded. | Harden gating with independent/cross-fitted evaluation, explicit fallback rules and additional edge-case tests; do not claim superiority without supporting results. |
| 7 | Ablation, robustness and streaming benchmark | **PASS — exploratory** | Model-side experiments include ablation, synthetic feature noise, bootstrap and importance analysis; replay/drain tests passed for 500, 5,000 and 20,000 messages. | Preserve measured evidence and avoid claiming production real-time behaviour, horizontal scalability or fault recovery from the single-worker setup. |
| 8 | Frozen test evaluation and maintenance demo | **EXECUTED; pushed and tagged** | Commit `8d6401c` and tag `phase-8-complete`; 46 tests passed; 707 prediction rows, 707 scored rows, four metric rows, 20 OOF audit rows and 707 maintenance recommendations. | Standardize this README and finish local documentation cleanup. Verify genuine pre-scoring protocol approval; otherwise retain exploratory status. Do not tune on these test scores. |
| 9 | Ensemble V2, interactive dashboard and SHAP | **PLANNED** | Not yet implemented as a complete interactive dashboard. | Improve and test the adaptive gate; build UI, evaluation/robustness/pipeline plots, local/global SHAP for the complete ensemble function, export and data-quality handling. |
| 10 | Research closure (original Phase 1) | **PLANNED** | Preliminary literature matrix and research notes exist. | Complete related-work reading, gap, protocol/cap decision and consistent research log. |
| 11 | Final integration and acceptance | **PLANNED** | Final acceptance not yet claimed. | Run end-to-end checks, verify docs/GitHub/tags, check no data/secrets/generated artifacts were committed, and rehearse the demo. |

## Phase 8 test-cohort results

The frozen Phase 8 run used a training RUL cap of 125 cycles and scored the official C-MAPSS test targets after writing the prediction-only output. The evaluation summary reports these results:

| Subset | Frozen method | Test engines | RMSE | MAE | NASA score sum |
|---|---|---:|---:|---:|---:|
| FD001 | `cross_window_no_disagreement` | 100 | 16.9346 | 12.4489 | 587.3681 |
| FD002 | `cross_window_error_gate` | 259 | 29.0353 | 20.3818 | 10330.7444 |
| FD003 | `cross_window_error_gate` | 100 | 18.2843 | 13.0945 | 1256.5902 |
| FD004 | `cross_window_no_disagreement` | 248 | 29.9007 | 22.3560 | 7928.2319 |

These are scores from the recorded frozen run, not proof of universal superiority or real-aircraft readiness. Because prior approval of the RUL cap and protocol has not been independently verified, treat them as **exploratory** unless genuine evidence confirms approval before scoring. Do not use this already-scored cohort for repeated tuning while presenting it as untouched.

## Maintenance demonstration

The Phase 8 maintenance demo writes `results/phase8/maintenance_recommendations.csv` from the saved predictions. Its `CRITICAL`, `HIGH` and `MONITOR` bands are illustrative project rules only; they are **not approved aviation maintenance instructions**.

## Repository guide

- `docs/project/architecture/phase_map.md` — phase map and architecture.
- `docs/project/data_validation_summary.md` — initial dataset validation.
- `docs/project/phase1_checklist.md`, `phase1_exit_criteria.md` and `docs/project/literature/` — open research/protocol work.
- `docs/project/phase2_*` — Kafka schema, test matrix, scope and results.
- `docs/project/phase3_*` — Spark/HDFS scope, runbook, validation and troubleshooting.
- `docs/project/phase4_*` — feature build, validation and runbook.
- `docs/project/phase5_*` — baseline protocols, runbook and validation results.
- `docs/project/phase6_*` — OOF ensemble protocol, results, runbook and troubleshooting.
- `docs/project/phase7_*` — ablation/robustness and streaming benchmark evidence.
- `docs/project/phase8_*` — frozen test-evaluation protocol, scope, runbook and summary.
- `docs/project/research_log.md` — chronological decisions, experiments and limitations.

## Reproduce the current checks

From the repository root in PowerShell, with the project virtual environment created and dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\scripts\phase8\maintenance_demo.py
```

Phase 8's official test evaluation has already been run. Do not rerun or retune it just to update the documentation or dashboard.

## Data and artifact policy

Raw C-MAPSS data, virtual environments, generated feature data, trained model files, local experiment outputs, caches and logs should remain outside Git unless a specific small artifact is intentionally curated for version control. Never commit credentials or secrets.

## Important limitations

- Phase 3 is a local integration on one Spark worker and one HDFS DataNode, not a production distributed or fault-tolerant deployment.
- Phase 7 throughput results are local replay/drain measurements; they do not establish concurrent real-time operation or horizontal scaling.
- Phase 6 is a candidate adaptive method. Its contribution must be assessed against baselines using a leakage-safe, documented validation protocol.
- Phase 8 risk tiers are illustrative only and are not maintenance advice.
- The original Phase 1 research protocol and novelty assessment remain open; no first-ever or universal-superiority claim is made.
