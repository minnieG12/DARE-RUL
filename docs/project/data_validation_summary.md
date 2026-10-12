# C-MAPSS Validation Summary

Date: 2026-10-12
Project: DARE-RUL

## Results

| Subset | Train rows | Train engines | Test rows | Test engines | RUL targets |
|---|---:|---:|---:|---:|---:|
| FD001 | 20,631 | 100 | 13,096 | 100 | 100 |
| FD002 | 53,759 | 260 | 33,991 | 259 | 259 |
| FD003 | 24,720 | 100 | 16,596 | 100 | 100 |
| FD004 | 61,249 | 249 | 41,214 | 248 | 248 |

## Structural Checks

- All four training files passed.
- All four test files passed.
- All four RUL target files passed.
- Engine-cycle structure and numeric data passed the validator checks.
- Test RUL target counts match the corresponding test engine counts.
- SHA-256 checksum manifest generated for 14 files.

## Interpretation

All four subsets passed the initial structural validation.

This does not prove the absence of every possible data issue. Additional
checks will be performed as preprocessing and modelling are implemented.

## Next Steps

1. Confirm the complete environment report.
2. Finish the literature matrix and identify the closest prior methods.
3. Select and document a reproducible baseline and evaluation protocol.
