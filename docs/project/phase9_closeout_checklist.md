# Phase 9 closeout checklist

- [x] Grouped nested validation executed for FD001–FD004.
- [x] Five outer engine-grouped folds per subset.
- [x] Three inner OOF folds and three gate/parameter-selection folds.
- [x] Official test files and official RUL labels not loaded.
- [x] 160,359 outer-fold prediction rows saved.
- [x] 32 method/subset metric rows saved.
- [x] V2 parameter-selection records and metadata saved.
- [x] No V2 fallback rows recorded.
- [x] V1/V2 comparison reviewed.
- [x] Decision recorded: V2 has no material gain; retain V1 as current candidate.
- [ ] Add this curated result note to the repository.
- [ ] Run the read-only validation script against the local output directory.
- [ ] Run full pytest once.
- [ ] Commit and push curated Phase 9 result note and validator.
- [ ] Leave the existing `phase-9-complete` tag unchanged; optionally add a new annotated `phase-9-nested-validation-complete` tag to the closeout commit.

No further V2 training/tuning is planned unless the mentor requests it.
