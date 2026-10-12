# Phase 4 Scope — Multi-Resolution Temporal Features

## Goal
Turn the raw NASA C-MAPSS engine-cycle readings into consistent features that describe both short-term (15-cycle) and longer-term (30-cycle) sensor behaviour.

## What the builder creates
For every sensor and each configured window, calculate trailing rolling mean, rolling standard deviation, and delta from the value one window-length behind (using the first available value for early cycles). Include current settings and sensor readings, engine ID, and cycle. Engine ID is retained for grouping, auditing and joining; do **not** use engine ID as a predictive model input. Use cycle, settings, current sensors and rolling features as candidate predictors.

- `train_features.parquet`: every training cycle, with uncapped RUL by default.
- `test_trajectory_features.parquet`: every observed test cycle, with no RUL label.
- `test_features.parquet`: final observed cycle per test engine, matching the evaluation point in the NASA test protocol.
- `test_targets.csv`: official RUL labels kept separate from feature tables.
- `metadata.json`: feature and row-count record per subset.
- `phase4_build_summary.json`: combined run summary.

## Leakage controls
- Rolling features use current and earlier cycles only.
- Calculations are grouped by engine; one engine's windows never contain another engine's readings.
- Test RUL labels are read only to create a separate target file. They are never joined into test feature tables.
- The train RUL cap is left unset by default because the Phase 1 protocol still needs mentor/team approval. A cap can be set later by passing `--rul-cap N` after that decision is recorded.

## Exit criteria
1. Five unit tests pass.
2. FD001–FD004 feature generation completes without malformed rows, duplicate engine-cycle pairs, or non-finite generated features.
3. Every test subset has exactly one final feature row and one target per test engine.
4. The run summary and per-subset metadata are saved locally and reviewed.
5. Code, tests, curated run summary and docs are committed; generated datasets stay local/ignored.

## Out of scope
This phase does not train or select models, decide the final RUL cap, establish predictive gains, prove novelty, or benchmark distributed scale. Those belong to Phase 1 decisions and Phases 5–7.
