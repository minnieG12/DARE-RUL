# Phase 8 — C-MAPSS test-cohort evaluation summary

**Execution status:** PASS. **Interpretation status:** Execution PASS; protocol approval evidence not verified, so interpret scores as exploratory.

## Procedure recorded by the implementation

- Training RUL cap: 125 cycles (provisional for research interpretation pending protocol closure).
- OOF folds: 5 engine-grouped folds over labeled training engines.
- The four final experts were fitted on labeled training engines; gate models were trained from engine-grouped OOF predictions only.
- Frozen per-subset methods: FD001/FD004 `cross_window_no_disagreement`; FD002/FD003 `cross_window_error_gate`.
- The generated run summary states prediction-only outputs were written before official targets were read for scoring. Official test targets were used for scoring only, not fitting/method selection.
- Test targets were scored uncapped; model predictions were clipped to the training cap.

## Results recorded by this run

| Subset | Frozen method | Engines | RMSE | MAE | NASA score sum | NASA score mean |
|---|---|---:|---:|---:|---:|---:|
| FD001 | `cross_window_no_disagreement` | 100 | 16.9346 | 12.4489 | 587.3681 | 5.873681 |
| FD002 | `cross_window_error_gate` | 259 | 29.0353 | 20.3818 | 10330.7444 | 39.887044 |
| FD003 | `cross_window_error_gate` | 100 | 18.2843 | 13.0945 | 1256.5902 | 12.565902 |
| FD004 | `cross_window_no_disagreement` | 248 | 29.9007 | 22.3560 | 7928.2319 | 31.968677 |

Artifact row counts: `test_predictions.csv` = 707, `test_scored_predictions.csv` = 707, `maintenance_recommendations.csv` = 707, `final_test_metrics.csv` = 4, `oof_fold_audit.csv` = 20.

## Protocol status

Protocol approval: **UNVERIFIED**. No independent approval record is present in the repository. The CLI flag in run metadata is not independent evidence. Treat these scores as exploratory pending protocol closure.

Do not change models, gates, cap, features, thresholds or method selections in response to these scores and still describe the same cohort as an untouched test set. Any future changes must use training/validation-only evidence.

## Limitations

- These are benchmark results for the NASA C-MAPSS simulated dataset, not validation on real aircraft.
- The current stream benchmark is a local setup with one Spark worker and one HDFS DataNode. It does not establish horizontal scalability, high availability, or failure recovery.
- CRITICAL/HIGH/MONITOR maintenance-demo tiers are illustrative rules, not approved aircraft maintenance policy.
- The transcript reports an elapsed time of 443454.516 seconds (~5.13 days), which is suspicious for a one-shot run; do not publish that runtime until its provenance is understood.

## Local generated artifacts (not normally committed)

- `results/phase8/test_predictions.csv`
- `results/phase8/test_scored_predictions.csv`
- `results/phase8/maintenance_recommendations.csv`
- `results/phase8/final_test_metrics.csv`
- `results/phase8/oof_fold_audit.csv`
- `results/phase8/run_metadata.json`
- `models/phase8/`
