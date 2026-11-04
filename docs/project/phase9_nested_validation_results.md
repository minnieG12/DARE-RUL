# Phase 9 — Grouped nested validation results and closeout

## Status

**Execution completed. Interpretation: exploratory training-only grouped nested validation.** The experiment used training feature Parquet files only. Metadata records that neither official test files nor official test RUL labels were loaded.

- Subsets: FD001–FD004
- Outer grouped folds: 5
- Inner OOF folds: 3
- V2 parameter-selection folds: 3
- Seed: 42
- RUL cap: 125, still provisional pending research-protocol closure
- Prediction rows: 160,359
- Method/subset metric rows: 32
- Parameter-selection rows: 720
- V2 fallback rows: 0 in all outer folds

## V1 versus nested-selected V2

Numbers below are read from `nested_cv_metrics.csv`. Differences are V2 minus V1; a positive error difference favours V1.

| Subset | V1 RMSE | V2 RMSE | Δ RMSE | V1 MAE | V2 MAE | Δ MAE |
|---|---:|---:|---:|---:|---:|---:|
| FD001 | 16.6359782 | 16.6359782 | 0.0000000 | 12.1068909 | 12.1068909 | ~0 |
| FD002 | 19.4289436 | 19.4289437 | +0.0000002 | 14.4545644 | 14.4545653 | +0.0000010 |
| FD003 | 14.5969825 | 14.5970012 | +0.0000188 | 9.4193815 | 9.4194162 | +0.0000348 |
| FD004 | 17.7076743 | 17.7076743 | ~0 | 12.2285062 | 12.2285062 | ~0 |

V1 and V2 are effectively indistinguishable on these outputs. V2 does not show a material performance improvement.

## Context against individual experts

- FD001: HGB30 is the best individual expert on RMSE (16.2751), MAE (11.6680) and NASA mean (6.1182). V1/V2 does not beat this individual expert.
- FD002: V1/V2 has the lowest RMSE among the listed methods (19.4289); HGB30 has slightly lower MAE (14.4454), while equal averaging has the lowest cycle-level NASA mean (13.0979).
- FD003: HGB30 is the best individual expert on RMSE (14.2192), MAE (8.9496) and NASA mean (5.0155). V1/V2 does not beat it.
- FD004: V1/V2 has the lowest RMSE (17.7077) and MAE (12.2285) among the listed methods; equal averaging has a lower cycle-level NASA mean (13.1525).

Metrics should be interpreted per subset. The cycle-level metrics aggregate many rows per engine; engine-macro metrics give each engine equal weight. Do not compare raw NASA score sums across subsets with different row counts as if they were directly comparable.

## What the parameter search selected

Every outer fold selected **shrinkage = 0.0**. Selected maximum weight varied between 0.65 and 0.8 on some subsets; the error floor was 0.5 throughout the reported selections.

This explains why nested-selected V2 closely reproduces V1: the selected configuration removes the shrinkage modification, and the remaining parameter changes do not materially alter the predictions.

## Decision

1. **Do not run another round of V2 tuning.** The mentor has indicated the current scope is sufficient.
2. Keep V1 as the reported adaptive candidate for the current project.
3. Keep V2 as a documented, evaluated variant that did not show a material gain.
4. Preserve the nested validation outputs as evidence.
5. Do not use Phase 8 official test scores to tune V1/V2 or to claim a new V2 test result.

## Interpretation and limitations

This is a stronger engine-grouped, nested training-only evaluation than the earlier simple reused validation comparison. However, earlier V2 experiments and Phase 6 validation results had already been inspected, so this should still be described as exploratory rather than a completely untouched independent confirmation.

The RUL cap of 125 remains provisional until the original research protocol is finalized. The metadata's elapsed time is 122,233.216 seconds (about 33.95 hours); verify the timer implementation before describing this as model-fitting runtime.

## Reproducibility files

- `nested_cv_metrics.csv`: aggregate metrics for 8 methods × 4 subsets
- `nested_cv_predictions.csv`: outer-fold held-out predictions
- `nested_cv_v2_parameter_selection.csv`: selected and rejected candidate settings
- `nested_cv_metadata.json`: data provenance, folds, seed and limitations
- `nested_cv_summary.md`: run-generated summary

Generated results remain local under `results/phase9/nested_validation/`; commit the curated interpretation document, not the large prediction CSV.
