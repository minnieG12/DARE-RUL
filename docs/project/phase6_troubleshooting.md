# Phase 6 Troubleshooting — validation error artifact length mismatch

## Symptom

The first Phase 6 run may fail near the end of the FD001 subset with an error similar to:

`ValueError: array length 4070 does not match index length 16561`

## Cause

The expected absolute-error predictions are generated for held-out validation rows, but the original artifact writer paired those arrays with engine/cycle keys from OOF training rows. The arrays therefore had different lengths. The OOF model fitting and the already-completed unit tests are not the cause.

## Fix

The patched code builds `adaptive_expected_errors_validation.csv` from validation engine/cycle keys (`val`) so that row keys and predicted-error values have the same rows and order. It also validates lengths, uniqueness and finite values before writing the file.

## Recovery

1. Apply the Phase 6 hotfix ZIP over the project root.
2. Run the Phase 6 unit tests.
3. Re-run the full Phase 6 script. It is safe to rerun: per-subset OOF files and gate models are recomputed/overwritten.
4. Continue only if the script prints `PHASE 6 ADAPTIVE ENSEMBLE RUN PASS`.

Official test RUL files remain unused. The fix does not change model definitions or the evaluation split; it corrects the validation artifact's row-key alignment.
