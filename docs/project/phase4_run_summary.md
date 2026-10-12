# Phase 4 Run Summary — Multi-Resolution Temporal Features

- **Status:** PASS
- **Generated:** 2026-10-12 23:18 UTC
- **Windows:** 15, 30 cycles
- **Training RUL cap:** Uncapped (Phase 1 cap decision still pending)
- **Automated feature tests:** 5 passed (run by `scripts/phase4/run_phase4.ps1` before the build).

## Build results

| Subset | Train engines | Train rows | Test engines | Test trajectory rows | Final test rows | Test targets | Feature columns | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| FD001 | 100 | 20631 | 100 | 13096 | 100 | 100 | 152 | PASS |
| FD002 | 260 | 53759 | 259 | 33991 | 259 | 259 | 152 | PASS |
| FD003 | 100 | 24720 | 100 | 16596 | 100 | 100 | 152 | PASS |
| FD004 | 249 | 61249 | 248 | 41214 | 248 | 248 | 152 | PASS |

## Checks and interpretation

- Features use current and previous cycles only; rolling windows are grouped by engine.
- Test RUL labels are stored separately in `test_targets.csv`, not inside test feature Parquet files.
- `engine_id` is retained for grouping and joining only; do not use it as a model input.
- Generated data is local under `data/features/phase4/` and should remain ignored by Git.
- Output-integrity validator tests passed.
- **Scope limit:** this PASS means feature generation completed and its checks passed. It does not prove predictive accuracy, a better ensemble, research novelty, or distributed scalability.
- **Next:** close the Phase 1 decisions on target cap, validation split, metrics and baselines before final model comparisons.

Machine-readable run evidence: `data/features/phase4/phase4_build_summary.json` (local/ignored).
