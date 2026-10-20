# DARE-RUL remaining work plan — Phases 3–11

Use this as the execution checklist. The Phase 8 evaluation has already run and its outputs must remain frozen.

## Phase 3 — Spark/HDFS verification
1. Run `scripts/phase3/inspect_hdfs_replication.ps1`.
2. Confirm configured replication, live DataNodes, block status, and the contents of `/dare-rul`.
3. Since configured `dfs.replication` was reported as 1, inspect the exact blocks/files flagged by fsck; do not assume the reported under-replication is caused by the current setting.
4. Retain the 500-row read-back evidence. Only add scale/recovery claims if a multi-worker/multi-DataNode/failure test is actually implemented and measured.

## Phase 4 — Features
1. Keep the generated features; don't rebuild unless code changes.
2. Retain the feature dictionary, engine grouping, current/past-only window explanation, early-window handling and feature validation tests.
3. Confirm identifiers and labels do not appear in predictor lists.

## Phase 5 — Baselines
1. Keep RF15/HGB15/RF30/HGB30 and their fixed settings.
2. Preserve engine-split validation, seed, cap used, metrics and model metadata.
3. Do not describe the baseline as an exact published-paper reproduction unless settings/protocols match.

## Phase 6 — Existing V1 adaptive ensemble
1. Preserve the Phase 6 tag and source as V1.
2. Document OOF prediction construction, engine group separation, error targets, sample weights, gate features and inverse-error blending.
3. Phase 9 V2 must not silently overwrite V1.

## Phase 7 — Robustness and streaming benchmark
1. Retain saved ablation/noise/bootstrap/feature-importance evidence.
2. Keep benchmark facts tied to saved CSV/run metadata.
3. Say local replay/drain; do not claim horizontal scaling, real-time concurrency, HA or recovery without tests.

## Phase 8 — Released
- Commit `8d6401c` was pushed and tagged `phase-8-complete`; a later README follow-up was pushed as `0d165d6` according to the user's transcript.
- Do not rerun official evaluation to tune a new method. Review output runtime metadata before publishing runtime.
- Keep `phase8_pack_readme.md` out of Git unless content is deliberately merged into maintained docs.

## Phase 9 — V2 + dashboard + SHAP
1. Copy the new `scripts/phase9`, `dashboard`, new tests and optional dashboard requirements into the repository (commands in pack README).
2. Run new helper tests before any model experiment.
3. Create a pre-registered validation comparison using engine-grouped training/validation only. Phase 6 validation has already been used for previous comparisons; label simple reuse exploratory, or implement nested/cross-fitted evaluation for the final V2 choice.
4. Compare V2 against each expert, equal averaging, static reliability weights and V1; add engine-level bootstrap intervals and ablations.
5. Launch dashboard; test fleet filters, evaluation plots, weights, export, pipeline summary and SHAP.
6. SHAP needs parity against saved Phase 8 output; if mismatch, block explanation and inspect feature schema/model/gate imports.
7. Commit in small logical units; tag only after all tests and docs are complete.

## Phase 10 — Original Phase 1 research closure
1. Finish full-text closest-paper review and populate the literature matrix.
2. Write a precise research gap grounded in cited evidence.
3. Document RUL cap, split, seeds, metrics, model selection and leakage controls.
4. Verify whether mentor/team approval actually occurred before Phase 8 scoring. If not, keep Phase 8 scores exploratory.
5. Record the decision, date, basis, limitations and update the research log/phase map.
6. Do not tune on the already-scored official test cohort while calling it untouched.

## Phase 11 — Acceptance
1. Run full pytest suite.
2. Run Kafka and Spark/HDFS smoke checks and compare Parquet row counts.
3. Verify feature, model and gate schemas and predictions.
4. Verify dashboard filters, downloads, SHAP parity and error handling.
5. Check Markdown links, UTF-8, README uniform format, stale phase claims and dependency instructions.
6. Inspect `git status`, staged filenames, large/ignored files, `git log`, remote `main`, and tags.
7. Rehearse a full demo and state limitations honestly.

## Later deliverables
Only after Phase 11 and Phase 10 are accepted: research paper, final project report and presentation.
