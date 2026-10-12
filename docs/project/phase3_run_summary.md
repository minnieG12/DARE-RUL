# Phase 3 Run Summary — Spark Structured Streaming + HDFS

**Status: PASS for the initial end-to-end smoke test.** This is one 500-event FD001/train run, not a scalability or failure-recovery benchmark.

## Run details

- Run label: `fd001_train_hdfsfix_20261013_031145`
- Date/time from local run: 2026-10-13 (container log timestamp: 2026-10-12 21:44 UTC)
- Spark version: 3.5.1; Java in Spark container: 11.0.24
- Kafka topic: `cmapss-p2-fd001-train-20261012150514886`
- Expected input messages: 500
- Runtime reported by the application: 34.34 seconds (first run included dependency resolution; not a steady-state latency metric)

## Data quality

| Check | Result |
|---|---:|
| Valid rows read back from Parquet | 500 |
| Invalid rows read back from invalid Parquet output | 0 |
| Duplicate `(dataset, split, engine_id, cycle)` pairs | 0 |
| Cycle-order warnings (per Kafka key, ordered by Kafka offset) | 0 |
| RUL/target leakage | None reported |

## Storage evidence

- Valid Parquet: `hdfs://namenode:9000/dare-rul/phase3/fd001_train_hdfsfix_20261013_031145/parquet`
- Invalid-record output: `hdfs://namenode:9000/dare-rul/phase3/fd001_train_hdfsfix_20261013_031145/invalid`
- Checkpoint root: `hdfs://namenode:9000/dare-rul/checkpoints/phase3/fd001_train_hdfsfix_20261013_031145`
- Output verification listed six Parquet part files plus `_spark_metadata` under the valid path, totaling about 105 KB in the reported HDFS count.
- The invalid path listed small Parquet part files, but Spark's read-back count reported 0 invalid rows. Empty micro-batch output files are possible; row counts, not just filenames, determine whether invalid records were present.
- Both `valid` and `invalid` query checkpoint directories were present in HDFS.

## Cluster and tests

- Spark Master and Worker running; Spark Master reported Spark 3.5.1.
- HDFS NameNode and DataNode healthy; 1 live DataNode with replication factor 1.
- Unit tests: `5 passed`.
- Non-fatal logs included the optional native Hadoop library warning and notices that adaptive query execution is disabled for streaming; the job completed with status `PASS`.

## Interpretation and limitations

This run demonstrates Kafka → Spark Structured Streaming → HDFS/Parquet with HDFS checkpoints for a known 500-event topic. It does not establish multi-worker scale-out, high-volume performance, restart recovery or production fault tolerance. Those remain later evaluation tasks.

## Machine-readable evidence

- Local summary: `results/phase3/fd001_train_hdfsfix_20261013_031145_summary.json` (ignored by Git; retain locally)
- Summary JSON values above were copied from the successful run output.
