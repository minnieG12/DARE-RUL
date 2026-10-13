# Phase 1 Research Follow-up — Open Items

The technical setup and C-MAPSS structural validation passed. The overall research-foundation exit remains pending.

- [ ] Read and record the closest full-text C-MAPSS/RUL and ensemble/adaptive-weighting papers. Do not count abstracts or search snippets as a full-text review.
- [ ] For each paper, record dataset subsets, target definition/cap, feature processing, split unit, baseline models, metrics, reported results, limitations, and relation to DARE-RUL.
- [ ] Confirm the RUL definition and whether to use a 125-cycle cap with the mentor/team. Phase 4 stored uncapped targets; Phase 5 used capped targets. Compare capped versus uncapped on validation only before freezing the choice.
- [ ] Confirm engine-separated split and seed. Current setting: 20% of engines held out, seed 42.
- [ ] Confirm baseline set. Current: RF15, HGB15, RF30, HGB30; Phase 6 adds equal averaging and training-only inverse-OOF-MAE weighting.
- [ ] Confirm metrics and their exact sign/penalty convention. Current: RMSE, MAE and PHM08/NASA score. Report row-weighted and engine-macro results.
- [ ] Compare the candidate adaptive error gate to the closest published ensemble, stacking, mixture-of-experts and adaptive weighting methods before writing a novelty claim.
- [ ] Freeze the official test evaluation plan before reading or using official test labels. Decide final-row-per-engine scoring, cap convention, metrics, baselines, ablations and repeat runs.

## High-priority related work to review first

These are **reading candidates**, not papers marked as fully reviewed. Access and read the full text, then extract the exact experimental protocol and limitations into the project's literature matrix.

1. **Official dataset definition:** NASA, “CMAPSS Jet Engine Simulated Data.” It is the authoritative source for the dataset splits, trajectories, operating settings and sensor columns. <https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data>
2. **Historical RUL method:** Felix O. Heimes, “Recurrent neural networks for remaining useful life estimation,” PHM 2008, DOI: <https://doi.org/10.1109/PHM.2008.4711422>. Extract its input preparation, target convention and evaluation protocol.
3. **Very close stacking paper:** “A multi-model stacked ensemble architecture with Bayesian optimization: Advancing remaining useful life estimation in aircraft engines,” Measurement (2025), DOI: <https://doi.org/10.1016/j.measurement.2025.120199>. Compare how its meta-learner, tuning protocol, split and results differ from DARE-RUL.
4. **Very close adaptive-expert paper:** Liang Zhou and Huawei Wang, “An adaptive multi-scale feature fusion and adaptive mixture-of-experts multi-task model for industrial equipment health status assessment and remaining useful life prediction,” Reliability Engineering & System Safety (2024), DOI: <https://doi.org/10.1016/j.ress.2024.110190>. This directly overlaps with adaptive expert fusion; it must be reviewed before making an originality claim.
5. **Metric definition:** confirm the PHM08/NASA asymmetric score definition and sign convention from a primary PHM challenge/reference source, and document the formula used by `scripts/phase5/baseline_core.py`.

Recent search results show that stacking and adaptive mixture-of-experts already exist in adjacent RUL literature. Therefore, DARE-RUL should not claim novelty merely for combining multiple models or weighting experts adaptively. A defensible gap, if one exists, must be narrower and supported by the full-text comparison.

## Evidence needed to close Phase 1

Update `phase1_checklist.md`, `phase1_exit_criteria.md`, the literature matrix and `research_log.md` only after the above decisions have evidence and mentor/team confirmation where required. Phase 6 engineering can proceed in parallel, but must not be presented as closing these research decisions.
