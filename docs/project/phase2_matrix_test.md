# Phase 2 expanded ingestion matrix

## Why this test is needed
The first FD001/train smoke test delivered 500 messages. However, the consumer starts from the earliest available topic offset; if the shared topic already had older events, those can be what it reads. This test gives each dataset/split combination a new topic, ensuring the consumer validates the events from that exact run.

## Coverage
FD001, FD002, FD003 and FD004, each for train and test. By default, the first 500 chronologically sorted rows from each file are replayed. This is a representative integration sample, not a full-dataset throughput benchmark.

## Passing criteria per scenario
- Producer enqueues and delivers the requested count.
- Producer has zero failed messages and zero outstanding messages after flush.
- Consumer reads and validates all expected messages.
- Invalid events and ordering warnings are zero.
- RUL/target labels are not placed in telemetry.

## Outputs
- Local log directory: `results/phase2/matrix_<run-id>/`
- Latest machine-readable summary: `docs/project/phase2_matrix_results.csv`

## Limits
The test does not replace repeatable high-load throughput/latency experiments, failure recovery tests, or later Spark/HDFS integration.
