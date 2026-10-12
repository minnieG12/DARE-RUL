# Phase 1 — Research-gap assessment (working version)

**Status:** Literature-scoping synthesis; candidate gap, not proof of novelty.

## What the literature already covers

1. **Ensemble RUL prediction:** prior studies combine prognostic models, use health-index grouping, accuracy-based weighting, degradation-stage selection and stacking. In particular, Han & Li (2023) use a health-index classification approach to select/adapt an ensemble; Li et al. (2023) use classification/clustering plus an accuracy-weighted ensemble; Ture et al. (2024) study stacking. See the DOI links in `literature_matrix_populated.csv`.
2. **Multiple time scales:** multiscale RUL approaches already exist, including a multi-scale attention-based TCN published in *Reliability Engineering & System Safety* (2024). Multiple windows alone are not novel.
3. **Big Data/streaming:** stream-processing architectures for predictive maintenance already exist. The 2026 *SoftwareX* Smart Factory paper specifically describes Kafka-based microservices and C-MAPSS-based deep RUL models. We must not claim the first Kafka + C-MAPSS implementation.
4. **Modern sequence models:** CNN, LSTM, TCN, Transformer, attention and graph-based methods are well represented in the RUL literature.

## Candidate research question

> Under a controlled and leakage-safe C-MAPSS evaluation protocol, does an interpretable adaptive gate over separate 15-cycle and 30-cycle Random Forest/Gradient Boosting experts improve RUL error or robustness compared with individual experts, fixed averaging, validation-error weighting and conventional stacking—and what is the cost of processing the telemetry through a Kafka–Spark–storage pipeline?

## Candidate contribution (to be tested, not asserted)

- Four transparent expert models: RF-15, GB-15, RF-30 and GB-30.
- A gate that combines: (a) current/past-only degradation-context features, (b) expert reliability estimated from training-only validation/out-of-fold predictions, and (c) disagreement among the expert point predictions.
- Non-negative expert weights that sum to one, so the combination is interpretable.
- A reproducible system evaluation measuring Kafka event delivery/order, throughput, processing latency, storage/checkpoint behavior and resource use separately from RUL accuracy.

This is best described as a **targeted modification/integration of established methods**, not a wholly new algorithm. The exact proposed gate must be compared with prior adaptive ensembles and stacking; the closest full texts and any new 2025–2026 studies should be rechecked before publication.

## Baseline decision for the implementation

Use a transparent, fair baseline ladder:
1. RF-15, GB-15, RF-30, GB-30 individually.
2. Uniform average of four experts.
3. Validation-error-weighted average.
4. Conventional `StackingRegressor` with out-of-fold meta-features.
5. Proposed context + reliability + disagreement gate.

These are project baselines informed by the literature. Do **not** call them an exact reproduction of a paper unless the original preprocessing, target definition, features, splits and reported settings have been reconstructed from the full paper. A closer published method can be reproduced as a separate experiment if its details and time allow.

## What would falsify the proposal?

The candidate gate is not supported if it fails to improve or provide a useful accuracy/robustness/cost trade-off over strong baselines, or if a close paper already describes an equivalent method. In that case, report the negative result and narrow the contribution. Never tune using official test RUL labels.
