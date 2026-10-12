# DARE-RUL Research and Experiment Log

## Project details
- Project: DARE-RUL — Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction
- Dataset: NASA C-MAPSS FD001–FD004
- Team / mentor: fill in
- Start date: fill in

## Research question (draft)
Can a multi-resolution ensemble of classical ML models, combined using validation-learned reliability and prediction-disagreement signals, improve C-MAPSS RUL estimates over comparable single models and fixed-weight ensembles, while being served by a measurable distributed ingestion/processing pipeline?

## Baseline protocol (to finalize from literature)
- Dataset subset(s):
- RUL labeling and cap protocol:
- Train / validation split method:
- Features and preprocessing:
- Baseline model configurations:
- Metrics: RMSE, MAE, NASA score (if protocol-aligned)
- Random seeds / repeated runs:

## Proposed method (hypothesis, not a novelty claim yet)
1. Build 15-cycle and 30-cycle feature views without using future observations.
2. Train comparable RF and Gradient Boosting experts on those views.
3. Estimate expert reliability using training/validation data only.
4. Derive a disagreement signal from expert predictions.
5. Compare a simple, bounded adaptive combiner against fixed averaging and individual experts.
6. Freeze all choices before evaluating on held-out test labels.

## Experiment register
| ID | Dataset | Features | Method | Config / seed | RMSE | MAE | NASA score | Runtime / latency | Notes |
|---|---|---|---|---|---:|---:|---:|---:|---|
| EXP-001 | | | | | | | | | |

## Decisions and limitations
Record assumptions, failures, deviations from the protocol, unavailable components and why they were deferred.
