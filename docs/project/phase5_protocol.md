# Phase 5 Baseline Protocol (Provisional)

- Dataset: NASA C-MAPSS FD001–FD004.
- Train/validation split: 80/20 by engine, fixed seed 42; no engine appears in both subsets.
- Target: `RUL = max_cycle_for_engine - cycle`, using the Phase 4 label; cap at 125 for this primary baseline run. Compare capped and uncapped targets in a sensitivity experiment before locking the research protocol.
- Predictors: settings, current sensor readings and 15- or 30-cycle trailing-window sensor mean/std/delta. Exclude `engine_id`, `cycle`, and `RUL` from predictors.
- Models: RandomForestRegressor (120 trees, max_features=0.7, min_samples_leaf=2) and HistGradientBoostingRegressor (150 iterations, learning_rate=0.08, max_leaf_nodes=31, L2=1.0). Fixed settings, random seed 42, no hyperparameter search.
- Metrics: RMSE, MAE and PHM08/NASA asymmetric score. Lower is better.
- Official test data: intentionally unused during Phase 5. Freeze model selection before official test evaluation.
- Status: a reproducible engineering baseline protocol; final protocol approval and close-paper comparison remain Phase 1 research tasks.
