# DARE-RUL step-by-step completion guide — Phases 3–11

Plain-language reference for the existing repository. Run each section in order. Don't rerun the Phase 8 official test evaluation to improve V2.

## Current verified Git state from the project owner's terminal transcript

- Phase 8 evaluation commit: `8d6401c`, pushed, tagged `phase-8-complete`.
- README consistency follow-up: `0d165d6`, pushed to `origin/main`.
- Existing Phase 2–7 tags are historical release points. Do not move/delete them.
- 46 existing tests passed before Phase 9 files were added.
- The only known local leftover was untracked `docs/project/phase8_pack_readme.md`; inspect/archive it rather than committing stale pack instructions.

## Phase 3 — Verify HDFS replication (no rebuild unless a problem is found)

**What happens:** read the configured replication setting, live DataNode report and HDFS block health. The inspection script does not change settings or delete files.

```powershell
Set-Location "E:\Projects\big data\DARE-RUL"
.\scripts\phase3\inspect_hdfs_replication.ps1
```

Review the full output. `dfs.replication=1` was recorded previously, but HDFS reported under-replicated blocks. Identify which files/blocks the `fsck` output flags and compare the requested replication shown there with the active configuration. Don't blindly run `-setrep`.

**Exit evidence:** saved/recorded configuration, live node count, fsck findings, and the existing 500-row Phase 3 Parquet read-back evidence. The current one-worker/one-DataNode deployment is a local integration, not a production cluster.

If documentation needs correction, edit the Phase 3 summary/runbook. Commit only real changes (see Git commands at the end). Keep the existing `phase-3-complete` tag unchanged.

## Phase 4 — Verify temporal feature integrity

**What happens:** ensure saved 15/30-cycle feature sets exist and match the documented schema; do not regenerate data unless code changed.

```powershell
Get-ChildItem .\data\features\phase4 -Recurse -File |
    Select-Object FullName, Length
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase4_features.py
```

If your installed repository uses the differently named Phase 4 validator, check it with `Get-ChildItem .\scripts\phase4` and run its `--help` before invoking it. Confirm in the report that feature windows are built per engine using current/past cycles, identifiers/targets are excluded from predictors, and official test targets remain separate.

**Exit evidence:** expected feature files/metadata exist and Phase 4 tests pass. Don't rerun the whole feature build solely to refresh docs.

## Phase 5 — Verify baseline reproducibility

**What happens:** validates baseline helper/test contracts without retraining all models.

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase5_baselines.py
Get-Content .\docs\project\phase5_protocol.md
Get-Content .\docs\project\phase5_run_summary.md
```

Confirm RF15/HGB15/RF30/HGB30, engine-level validation split, seed, cap used, metrics and excluded identifier/target fields agree. Do not re-run baseline training unless you are intentionally starting a separate validation experiment.

**Exit evidence:** baseline tests pass and settings/results are documented together.

## Phase 6 — Preserve V1; V2 is a new experiment

**What happens:** current Phase 6 remains the tagged V1. Phase 9 V2 introduces a bounded, shrinkage-stabilized blending helper and compares it with V1 and baselines on existing validation artifacts.

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase6_ensemble.py
Get-Content .\docs\project\phase6_protocol.md
Get-Content .\docs\project\phase6_run_summary.md
```

Don't overwrite `scripts/phase6/ensemble_core.py` or move `phase-6-complete`. The V2 helper is located at `scripts/phase9/ensemble_v2.py` after the pack is copied in.

## Phase 7 — Verify robustness and streaming benchmark records

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_phase7_experiments.py
Get-Content .\docs\project\phase7_run_summary.md
Get-Content .\docs\project\phase7_streaming_benchmark_summary.md
```

Use the saved Phase 7 output and summary as evidence. Don't rerun a 20,000-message streaming benchmark unless the pipeline code changed or you are deliberately repeating a measured benchmark. The current single-worker/single-DataNode replay/drain results don't prove horizontal scaling, real-time concurrency, high availability, or recovery.

## Phase 8 — Already released

The Phase 8 evaluation was pushed as `8d6401c` and tagged `phase-8-complete`; README consistency follow-up `0d165d6` was pushed later. Don't rerun official test scoring. Review `results/phase8/run_metadata.json` and the Phase 8 summary together; the elapsed time `443454.516` seconds is suspicious and should not be published as runtime until the timer provenance is understood.

The local `docs/project/phase8_pack_readme.md` was stale and untracked. To preserve it outside Git before removing it from the repo:

```powershell
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item .\docs\project\phase8_pack_readme.md `
    "$env:TEMP\phase8_pack_readme_archived_$Stamp.md"
Remove-Item .\docs\project\phase8_pack_readme.md
```

Only do this after confirming its useful information is already present in `phase8_protocol.md` and `phase8_runbook.md`. This does not alter the tagged release.

## Phase 9 — Improved adaptive ensemble, dashboard and SHAP

### 9A. Copy the new files

Extract this pack to a temporary folder. Set `$Pack` to the folder containing this README, then run from the project root:

```powershell
$Project = "E:\Projects\big data\DARE-RUL"
Set-Location $Project

Copy-Item "$Pack\dashboard" . -Recurse -Force
Copy-Item "$Pack\scripts\phase9" .\scripts -Recurse -Force
Copy-Item "$Pack\tests\test_phase9_ensemble_v2.py" .\tests -Force
Copy-Item "$Pack\tests\test_phase9_dashboard_data.py" .\tests -Force
Copy-Item "$Pack\requirements-dashboard.txt" . -Force
Copy-Item "$Pack\docs\project\phase9_dashboard_shap_spec.md" .\docs\project -Force
Copy-Item "$Pack\docs\project\project_completion_plan_phases3-11.md" .\docs\project -Force
Copy-Item "$Pack\docs\project\step_by_step_remaining_phases3-11.md" .\docs\project -Force
Copy-Item "$Pack\docs\project\phase9_demo_checklist.md" .\docs\project -Force
Copy-Item "$Pack\scripts\phase3\inspect_hdfs_replication.ps1" .\scripts\phase3 -Force

.\.venv\Scripts\python.exe -m pip install -r .\requirements-dashboard.txt
.\.venv\Scripts\python.exe -m pytest -q
```

**What happens:** installs only optional UI/XAI dependencies, copies new Phase 9 helpers/tests, and runs the full suite. Expect 46 existing tests plus 7 new pack tests (53 total) if all files copy successfully.

### 9B. Smoke-test the V2 combiner on existing Phase 6 validation outputs

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
    .\tests\test_phase9_ensemble_v2.py `
    .\tests\test_phase9_dashboard_data.py

.\.venv\Scripts\python.exe .\scripts\phase9\run_ensemble_v2_validation.py `
    --subsets FD001 FD002 FD003 FD004 `
    --bootstrap-reps 500
```

Outputs go under ignored `results/phase9/`. This reuses Phase 6's already-used validation cohort, so its V2 comparison is explicitly **exploratory**. It must not be used to claim an untouched estimate. Do not pass any Phase 8 test target or score to this script. Inspect:

```powershell
Import-Csv .\results\phase9\ensemble_v2_validation_metrics.csv |
    Format-Table subset, method, rmse, mae, nasa_score_mean -AutoSize
Get-Content .\results\phase9\ensemble_v2_validation_metadata.json
```

Do not call V2 an improvement unless comparisons support it. For final research selection, implement nested/cross-fitted grouped validation or another independently specified validation design.

### 9C. Check model parity before SHAP

```powershell
.\.venv\Scripts\python.exe .\scripts\phase9\check_phase8_model_parity.py `
    --subsets FD001 FD002 FD003 FD004 --engines-per-subset 1
```

**What happens:** loads the saved Phase 8 expert/gate models and feature tables, reconstructs one selected engine prediction per subset, and checks that it matches the saved prediction. If it fails, stop and debug model paths, features, or gate schemas. SHAP is deliberately blocked when parity fails.

### 9D. Start the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\dashboard\app.py
```

Test all pages using the checklist in `docs/project/phase9_demo_checklist.md`. Begin SHAP with two to four training background rows and one permutation; it can be CPU-intensive with 152 features. The SHAP code uses the project's original `scripts/phase7/phase7_core.py`, which was present in the repository but omitted from the uploaded source snapshot; don't overwrite it.

The dashboard must clearly state that SHAP values explain the model relative to a training background and are not causal proof. Risk tiers remain illustrative, not maintenance advice.

### 9E. GitHub progress for Phase 9

Commit the V2 helper/validation files as one logical commit after tests and review; dashboard files can be a second commit after parity and UI checks. See the final section below. Create `phase-9-complete` only after both V2 acceptance and dashboard/SHAP acceptance genuinely pass.

## Phase 10 — Close the original Phase 1 research work

Do this only after implementation through Phase 9 is stable.

1. Finish full-text review of the closest C-MAPSS RUL, multi-resolution features, adaptive/stacked ensemble, model-selection and explainability papers.
2. Complete `docs/project/literature/literature_matrix_populated.csv` with datasets, label cap, splits, features, models, metrics and limitations for each paper.
3. Write a precise, evidence-backed gap; do not infer novelty from simply combining technologies/models.
4. Finalize the cap (currently 125), engine-level split, seed, metrics, baselines, selection procedure and leakage protections.
5. Verify whether real mentor/team approval occurred before Phase 8 scoring. If not provable, retain Phase 8 metrics as exploratory. Never rewrite history to set approval true.
6. Record the decision/evidence/date and update `research_log.md`, Phase 1 checklist, protocol files and README consistently.
7. Do not use Phase 8 official scores to tune V2 while claiming the same test cohort is untouched.

Only mark Phase 10 complete when all Phase 1 exit criteria are met and the literature/research gap has been reviewed.

## Phase 11 — Final integration and acceptance

1. Full tests: ` .\.venv\Scripts\python.exe -m pytest -q `.
2. Verify Kafka with ` .\scripts\kafka\verify_kafka.ps1 `.
3. Verify Spark/HDFS with ` .\scripts\phase3\verify_phase3_cluster.ps1 ` and inspect output using the relevant Phase 3 output verifier/runbook.
4. Run the model-parity script for all four subsets.
5. Test all dashboard filters/plots/downloads and one SHAP explanation per subset.
6. Run the documentation checker available in the runbook pack; review false-positive flags manually.
7. Check Git diff, current branch, remote `main`, tags, line endings, ignore rules and absence of data/models/results/secret files from the staged set.
8. Rehearse telemetry → HDFS/Parquet → feature/model flow → adaptive gate → metrics → dashboard → SHAP → limitations.
9. Only then tag `phase-11-complete`.

## Git command pattern for every released milestone

Use consistent `phase-N: ...` commit messages and do not commit outputs. For each phase where real files changed:

```powershell
git status --short --untracked-files=all
git diff --check
# Stage only reviewed files, e.g.:
# git add scripts/phase9/ensemble_v2.py tests/test_phase9_ensemble_v2.py docs/project/phase9_dashboard_shap_spec.md
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
# Commit only after the staged list is correct:
# git commit -m "phase-9: add bounded adaptive ensemble validation"
git fetch origin
git status -sb
git push origin main
git status
git log -5 --oneline --decorate
```

If remote has diverged or unexpected commits, stop and reconcile; do not force-push. Create annotated phase tags only after exit criteria pass and the associated commit is on `origin/main`. Don't move existing Phase 2–8 tags.

## Later deliverables

After Phases 10 and 11 pass: research paper, final project report and presentation.
