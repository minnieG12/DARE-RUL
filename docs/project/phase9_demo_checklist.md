# Phase 9 demo checklist

- [ ] Dashboard loads saved artifacts without modifying/re-running Phase 8.
- [ ] Subset, risk tier and search filters work.
- [ ] Fleet table and CSV export match the filtered rows.
- [ ] Metric table, prediction-vs-target plot and error histogram work.
- [ ] Selected engine shows four expert predictions, expected errors, weights and final RUL.
- [ ] SHAP parity check passes before attributions are displayed.
- [ ] SHAP background is sampled from training feature rows; identifiers/targets are not explainer inputs.
- [ ] SHAP plots show units as model-attribution contributions to predicted RUL cycles.
- [ ] Pipeline tab labels results as local replay/drain evidence.
- [ ] UI explicitly states predictions are for the NASA C-MAPSS benchmark and risk tiers are not maintenance advice.
- [ ] New tests pass; full test suite passes.
