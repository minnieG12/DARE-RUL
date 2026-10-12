# DARE-RUL

**Distributed, Multi-Resolution Adaptive Ensemble for Remaining Useful Life Prediction**

Research prototype for Remaining Useful Life (RUL) prediction on NASA C-MAPSS FD001–FD004, with a Kafka/Spark data pipeline and a proposed adaptive ensemble.

## Project rule

Raw dataset files and existing study documents stay local. Generated code and project-specific documentation are maintained in Git. See `README_PHASE0_1.md` in the setup bundle for the exact beginner-friendly commands.

## Research integrity

Adaptive weighting is a proposed method to test, not a guaranteed improvement. Model selection and adaptive weights must use training/validation data only; the held-out test labels are reserved for final evaluation.
