# Phase 8 Runbook (PowerShell / Windows)

Run from repository root: `E:\Projects\big data\DARE-RUL`.

## Prerequisites

- Phase 4 passed and the following files exist for every subset under `data/features/phase4/FDxxx/`: `train_features.parquet`, `test_features.parquet`, and `test_targets.csv`.
- Phase 5–7 code is present in `scripts/phase5`, `scripts/phase6`, and `scripts/phase7`.
- Project `.venv` includes the dependencies already used by prior phases, including pandas, numpy, scikit-learn, joblib, pyarrow and pytest.
- Before calling results final, confirm the cap and metric/split protocol with the team/mentor. The code defaults to cap 125 to match Phases 5–7. If approval is not recorded before the run, results are explicitly labelled exploratory.

## Run once

First repair a known PowerShell 5.1 encoding issue in the Phase 7 Markdown (the earlier documentation helper wrote mojibake into README/research log):

```powershell
cd "E:\Projects\big data\DARE-RUL"
.\.venv\Scripts\python.exe .\scripts\phase8\repair_phase7_docs_encoding.py
```

Then verify prerequisites and run the evaluation:

```powershell
Test-Path .\data\features\phase4\FD001\train_features.parquet
Test-Path .\data\features\phase4\FD001\test_features.parquet
Test-Path .\data\features\phase4\FD001\test_targets.csv

.\.venv\Scripts\python.exe -m pytest .\tests\test_phase8_final_eval.py -q
.\scripts\phase8\run_phase8.ps1
```

The run performs five engine-grouped folds across all train engines per FD subset, fits four final experts on all training engines, fits the selected error gates on OOF training-engine predictions, writes test predictions, and only then reads official target values to score predictions. It can take several minutes depending on the computer.

If the team/mentor has approved the 125-cycle cap and the rest of the protocol before running, use `.\scripts\phase8\run_phase8.ps1 -ProtocolApproved` instead. Do not set this switch merely to remove a warning; it records an actual protocol decision. Without approval, results are generated but labelled exploratory.

## Outputs (local; do not commit large files)

- `models/phase8/FDxxx/`: final expert and gate models plus gate feature specifications.
- `results/phase8/test_predictions.csv`: predictions only, without official targets; used by the maintenance demo.
- `results/phase8/test_scored_predictions.csv`: predictions joined with official RUL for scoring/audit.
- `results/phase8/final_test_metrics.csv`: per-subset final metrics.
- `results/phase8/final_test_summary.md`: human-readable scores and limitations.
- `results/phase8/oof_fold_audit.csv`: checks that OOF validation engines were held out by engine.
- `results/phase8/run_metadata.json`: seed, cap, selected methods, folds and label-use policy.

The runner refuses to rerun when final prediction/metric files already exist. If the run was interrupted for a technical reason, inspect and back up its partial outputs before explicitly using `--overwrite`. Do not rerun to pick another method after seeing official scores.

## Update project progress from actual test scores

After `final_test_metrics.csv` is generated, run this UTF-8-safe helper. It copies the generated result report into `docs/project/phase8_final_test_summary.md` and updates the marked Phase 8 sections in README and research log from the actual four-subset metrics; it refuses to write if the evaluation is incomplete.

```powershell
.\.venv\Scripts\python.exe .\scripts\phase8\update_phase8_docs.py
```

Review the resulting diffs before committing.

## Maintenance demo (CSV)

```powershell
.\.venv\Scripts\python.exe .\scripts\phase8\maintenance_demo.py
```

Outputs `results/phase8/maintenance_recommendations.csv`. By default, predicted RUL <= 10 is CRITICAL, <= 30 is HIGH and above 30 is MONITOR. These are placeholder demo thresholds and must not be presented as approved aircraft maintenance instructions.

## Optional dashboard

```powershell
.\.venv\Scripts\python.exe -m pip install streamlit
.\.venv\Scripts\python.exe -m streamlit run .\scripts\phase8\maintenance_dashboard.py
```

The dashboard displays prediction-based risk tiers only; it does not read official targets to create recommendations.

## Common issues

- Missing parquet/targets: run `scripts/phase4/run_phase4.ps1` and ensure the raw files are under `data/CMAPSSData/`.
- `No module named pyarrow`: inside `.venv`, run `python -m pip install pyarrow`.
- OOF fold error: there must be at least two unique training engines per subset, and `--oof-folds` cannot exceed engine count.
- Schema mismatch: do not drop or rename feature columns to force a run; compare Phase 4 outputs for train and test.
- Output-exists guard: use `--overwrite` only for technical recovery after backing up outputs, not for testing alternate methods on the official test set.
