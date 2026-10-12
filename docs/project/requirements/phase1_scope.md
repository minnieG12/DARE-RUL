# Phase 1 Scope and Decisions

## Purpose
Phase 1 checks that the original data is readable and establishes a repeatable research process before the distributed pipeline is built.

## Data handling
- Use the extracted dataset at `data/CMAPSSData/`.
- Leave original files unchanged.
- Do not commit the raw files to Git.
- Keep a SHA-256 manifest to detect accidental changes.

## Starter data checks
- Required 12 train/test/RUL files exist.
- Train/test sensor files have 26 numeric columns.
- No missing/non-finite values or duplicate engine-cycle pairs.
- Cycles increase within each engine.
- Derived training RUL reaches zero at each engine's final observed cycle.
- Each RUL target file has one target per test engine.

These are initial integrity checks, not a replacement for reviewing the C-MAPSS documentation and confirming the study's exact preprocessing protocol.

## Research protocol
- Review papers closest to C-MAPSS ensembles, adaptive weighting, multi-resolution features, and streaming/distributed predictive maintenance.
- Choose and document a fair baseline before final claims.
- Use validation data for model selection, expert reliability and adaptive weights.
- Hold out test targets for final evaluation only.
- Report failures and negative results honestly.
