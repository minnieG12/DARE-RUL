# Phase 5 Runbook

1. Confirm Phase 4 passed and the four `data/features/phase4/FDxxx/train_features.parquet` files exist.
2. From the DARE-RUL root, run `scripts/phase5/run_phase5.ps1`. The wrapper runs six focused unit tests before training.
3. The Python runner creates one fixed engine-separated split per FD subset and uses exactly the same split for the four models.
4. It trains RF15, HGB15, RF30 and HGB30 with fixed settings and no parameter search.
5. Review `docs/project/phase5_run_summary.md` and local `results/phase5/validation_metrics.csv`.
6. Ensure generated results and saved models remain ignored by Git. Commit the source code, tests and curated summary only.

## Outputs (local, ignored)
- `results/phase5/validation_metrics.csv`
- `results/phase5/validation_predictions.csv`
- `results/phase5/run_metadata.json`
- `models/phase5/FDxxx/*.joblib` and model metadata

## Failure handling
- Missing phase4 parquet: rerun `scripts/phase4/run_phase4.ps1`.
- Missing package: check `requirements-base.txt`; in the project virtual environment run `python -m pip install -r requirements-base.txt`.
- Unit test failure: stop and fix before fitting models.
- If a model run fails, do not commit a PASS summary. Send the entire error output and the subset/model name that failed.
- Models may take several minutes; do not interrupt unless the console shows an error or the process is clearly stalled.
