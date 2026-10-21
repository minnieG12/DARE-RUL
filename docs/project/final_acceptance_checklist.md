# Final acceptance checklist

## Environment and tests
- [ ] `git fetch origin` succeeds; local `main` equals `origin/main`.
- [ ] `git status -sb` is clean before a release.
- [ ] `.\.venv\Scripts\python.exe -m pytest -q` passes.
- [ ] Dashboard modules compile.
- [ ] Docker services start using documented commands.

## Test-data integrity
- [ ] Train/validation splits group all cycles from an engine together.
- [ ] Official `RUL_FD00*.txt` labels are not input features, gate training labels, SHAP features or hyperparameter-tuning feedback.
- [ ] Phase 8 prediction-only CSV precedes label scoring in the documented run.
- [ ] Historical Phase 8 scores are not presented as V2 test results.
- [ ] Test counts and subset mapping match the recorded 707 engines.
- [ ] RUL-cap/protocol approval is reported truthfully.

## Dashboard and SHAP
- [ ] Fleet filters and searchable engine table work.
- [ ] Evaluation charts use saved metrics and clearly separate prediction from scored data.
- [ ] Ensemble page shows expert predictions and blending/gate information.
- [ ] SHAP local explanation completes for a selected engine.
- [ ] Global SHAP overview completes on its bounded default sample.
- [ ] Prediction reconstruction matches saved output within a documented floating-point tolerance.
- [ ] IDs, cycle index and target labels are excluded from model explanation inputs.
- [ ] CSV export works.
- [ ] The pipeline page displays the 500/5,000/20,000 results, elapsed time, throughput and integrity counts.

## Documentation / Git
- [ ] README uses one format consistently for all phases.
- [ ] No known mojibake remains in Markdown.
- [ ] Relative links resolve.
- [ ] Phase 3 report states one DataNode and does not claim redundancy.
- [ ] Phase 7 report labels the benchmark local replay/drain.
- [ ] Phase 9 V2 report says it underperformed V1 on the reused cohort.
- [ ] Research log and phase status agree.
- [ ] Raw data, `.venv`, models, generated outputs, caches and secrets are not committed.
- [ ] Phase 8/9 tags point to the expected release commits.
- [ ] Phase 10/11 tags are not created until those phases really pass.

## Demo rehearsal
- [ ] Show Kafka -> Spark -> HDFS evidence.
- [ ] Explain 15/30-cycle feature windows.
- [ ] Explain four experts and V1 adaptive gate.
- [ ] Show the exploratory V2 comparison honestly.
- [ ] Show dashboard evaluation and SHAP.
- [ ] Explain official test-label usage and limitations.
