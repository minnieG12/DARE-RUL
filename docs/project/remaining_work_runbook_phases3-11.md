# Remaining-work runbook, Phases 3–11

Run these in order. These are simple project steps; don't rerun expensive experiments unless code or protocol changed.

## A. Phase 3: bring the local HDFS replica setting into agreement

The inspection showed one live DataNode, a configured default replication of 1, 680 under-replicated blocks, zero missing blocks and zero corrupt blocks. Some existing project blocks individually request replication 3. That is inconsistent with a one-DataNode local profile.

For the **local single-DataNode demo only**, set replica count to 1 without changing file contents:

```powershell
docker exec dare-rul-namenode hdfs dfs -setrep -w 1 -R /dare-rul
docker exec dare-rul-namenode hdfs fsck /dare-rul -files -blocks | Select-String "Under-replicated blocks|Missing blocks|Corrupt blocks|filesystem under path"
```

Check the output. Expected: under-replicated 0, missing 0, corrupt 0, healthy path. If these paths must retain replication factor 3, don't run setrep; instead add enough DataNodes and validate the three replicas. Document which profile was used.

## B. Phases 4–7: verify, then leave completed artifacts intact

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase4_features.py
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase5_baselines.py
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase6_ensemble.py
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase7_experiments.py
```

Review the respective `phase*_protocol.md`, `phase*_run_summary.md` and the streaming summary. Keep raw features/models/results out of Git. The current single-worker benchmark should be described as local replay/drain only.

## C. Phase 8: don't rerun scoring

Phase 8 is already pushed/tagged and its 707-row outputs exist. Retain `phase-8-complete`. Keep the protocol approval state honest; a metadata Boolean is not proof of actual prior approval.

## D. Apply dashboard polish

Extract this pack to a temporary directory and set `$Pack` to the extracted folder containing `dashboard`, `tests`, and `docs`:

```powershell
$Project = "E:\Projects\big data\DARE-RUL"
Set-Location $Project
Copy-Item "$Pack\dashboard\app.py" .\dashboard\app.py -Force
Copy-Item "$Pack\dashboard\pipeline.py" .\dashboard\pipeline.py -Force
Copy-Item "$Pack\tests\test_phase9_pipeline_ui.py" .\tests\test_phase9_pipeline_ui.py -Force
Copy-Item "$Pack\docs\project\phase9_v2_results_interpretation.md" .\docs\project\phase9_v2_results_interpretation.md -Force
Copy-Item "$Pack\docs\project\dashboard_ui_polish.md" .\docs\project\dashboard_ui_polish.md -Force
.\.venv\Scripts\python.exe -m py_compile .\dashboard\app.py .\dashboard\pipeline.py
.\.venv\Scripts\python.exe -m pytest -q
```

Expected 56 passed if the existing 53 tests are unchanged. Review `README_uniform_update.md` in this pack, merge it into the root README after checking every status, and don't blindly overwrite future changes.

Run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\dashboard\app.py
```

Pipeline page checks: title is “Streaming Pipeline Performance”; workload cards show 500, 5,000 and 20,000 messages; throughput is 17.05, 84.25, 131.78 rows/s; elapsed time is 29.33, 59.35, 151.77 seconds; all recorded data-quality checks display pass; no raw phase-specific document heading appears.

SHAP checks: select one subset and one engine; click Calculate SHAP; confirm parity pass and an attribution chart renders and CSV export works. Then try the global overview with the default small sample. Save the output/screenshot for demo evidence. A launched app or parity on four sample engines is not the same as successful SHAP calculation.

## E. Decide V2 correctly

The recorded V2 RMSE and MAE are worse than V1 on all four subsets. Don't tune the current hyperparameters further on the reused Phase 6 validation cohort. Keep V2 as an exploratory negative result.

Next: implement a separate nested engine-grouped validation experiment using training engines only. Within each outer fold, generate inner OOF expert predictions, fit the gates/static weights only from outer-training evidence, then evaluate on outer-held-out engines. Select parameters only inside inner folds. Compare V1, V2, simple average, static OOF weights and the best single expert with RMSE, MAE, NASA score, engine-macro metrics and paired engine-block intervals.

## F. Phase 10 research closure (original Phase 1)

1. Finish the closest-paper reading and fill the existing literature matrix with dataset/split/cap/features/methods/metrics/limitations.
2. Write a narrow, evidence-backed research gap rather than claiming novelty from tool combination alone.
3. Finalize the RUL cap, data split, seeds, metrics, selection rule and leakage safeguards.
4. Record actual mentor/team approval if it happened before Phase 8 scoring. If not verifiable, keep Phase 8 scores exploratory.
5. Update `research_log.md`, Phase 1 checklist/exit criteria and README consistently.
6. Do not use the already-scored official cohort to tune and then describe it as untouched.

## G. Phase 11 final acceptance

- Full tests pass.
- HDFS replication profile is verified and documented.
- Kafka → Spark → HDFS readback is verified.
- Phase 4 feature separation and Phase 6 OOF/gate leakage rules remain tested.
- V1/V2 comparison is documented with honest validation limits.
- Dashboard filters, tables, downloads and charts work.
- At least one local SHAP and one sample-based global SHAP explanation calculate successfully.
- README, phase summaries and research log have no stale statuses or mojibake.
- `git status -sb` is clean, main is pushed, and tags point to the intended commits.
- Demo is rehearsed with honest limitations.

## Git sequence

After reviewing staged files, use the matching phase prefix:

```powershell
# Phase 3 HDFS resolution (only after successful verification and docs update)
git add docs/project/phase3_scope.md docs/project/phase3_run_summary.md
git diff --cached --check
git commit -m "phase-3: align local HDFS replication with single-node profile"
git push origin main

# Dashboard/UI follow-up
git add dashboard/app.py dashboard/pipeline.py tests/test_phase9_pipeline_ui.py
git add docs/project/phase9_v2_results_interpretation.md docs/project/dashboard_ui_polish.md README.md
git diff --cached --check
git diff --cached --stat
git commit -m "phase-9: polish pipeline dashboard and document V2 results"
git push origin main

# Phase 10 and Phase 11 commands are only used after each is genuinely completed.
```

The existing `phase-9-complete` tag points to the previously committed dashboard implementation. Do not move it to a new commit without an intentional release/tagging decision. Do not create `phase-10-complete` or `phase-11-complete` until their acceptance criteria actually pass.
