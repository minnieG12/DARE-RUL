# Phase 3 Scope — Distributed Processing and HDFS

## Objective
Use a Spark standalone master/worker cluster to read validated DARE-RUL telemetry from Kafka, parse and quality-check JSON events, and persist valid data as Parquet in HDFS. Invalid events are routed separately. Streaming checkpoints are written to HDFS.

## Main components
- Apache Spark 3.5.1 (Docker image `spark:3.5.1`; Java 11 and Python 3 are included in this image).
- Spark Structured Streaming Kafka connector `spark-sql-kafka-0-10_2.12:3.5.1`.
- Hadoop HDFS NameNode and DataNode (single DataNode for the local prototype; replication factor 1).
- Kafka topic from the Phase 2 matrix (unique topic with 500 messages).
- Parquet as a columnar data format for later analytics/modeling.

## Processing
1. Read Kafka records from earliest offsets with a new checkpoint.
2. Cast key/value and preserve topic, partition, offset, and timestamp metadata.
3. Parse JSON into the canonical telemetry schema.
4. Reject malformed records, missing/non-finite sensors and any RUL/target field.
5. Write valid records to HDFS Parquet and invalid records to a separate HDFS folder.
6. Checkpoint both streaming queries in HDFS.
7. Run post-write count, duplicate engine-cycle, and cycle-order checks based on Kafka offsets.

## Exit criteria
- Spark master and worker are up and Spark UI is available.
- HDFS NameNode and DataNode are healthy.
- A clean Phase 2 topic is processed by Spark Structured Streaming.
- Expected count matches (500 for the initial run), invalid count is zero, duplicate engine-cycle pairs are zero, ordering warnings are zero, and target leakage is absent.
- Parquet parts and streaming checkpoints are visible in HDFS.
- Run summary and tests are committed and pushed to GitHub.

## Limits of this initial run
A single Spark worker and one HDFS DataNode prove the end-to-end integration locally; this is not a multi-worker scalability benchmark or failure-recovery study. Those belong in the later evaluation phase.
