# Phase 2 Run Summary — Kafka Telemetry Ingestion

**Status:** Expanded ingestion matrix passed. High-load scalability and failure-recovery experiments remain for Phase 7.

## Setup

- Kafka: 3.7.0; ZooKeeper: 3.9.3
- Topic design: a unique topic per dataset/split scenario, 4 partitions, replication factor 1
- Host bootstrap: `localhost:9092`; Docker-internal bootstrap: `kafka:9093`
- Replay method: first 500 chronologically sorted rows per scenario from historical C-MAPSS files; this simulates telemetry and is not live aircraft data.
- Payload excludes RUL/target labels.

## Expanded matrix

| Dataset | Split | Delivered | Validated | Producer rate (msg/s) | Consumer rate (msg/s) | Ordering warnings | Status |
|---|---|---:|---:|---:|---:|---:|---|
| FD001 | train | 500 | 500 | 98.80 | 154.03 | 0 | PASS |
| FD001 | test  | 500 | 500 | 99.84 | 154.74 | 0 | PASS |
| FD002 | train | 500 | 500 | 99.85 | 133.15 | 0 | PASS |
| FD002 | test  | 500 | 500 | 99.69 | 154.57 | 0 | PASS |
| FD003 | train | 500 | 500 | 99.81 | 153.74 | 0 | PASS |
| FD003 | test  | 500 | 500 | 99.93 | 154.90 | 0 | PASS |
| FD004 | train | 500 | 500 | 99.90 | 132.02 | 0 | PASS |
| FD004 | test  | 500 | 500 | 98.78 | 133.44 | 0 | PASS |

**Total:** 8/8 scenarios passed; 4,000 messages delivered and 4,000 validated in isolated test topics; no ordering warnings.

## Initial shared-topic run (historical caveat)

The first smoke test reported 500 deliveries, but its consumer used `auto.offset.reset=earliest` on the shared topic and first displayed key `FD001_train_2`, cycle 1. That run alone did not prove it consumed the exact batch just produced. The unique-topic matrix above resolves this issue for the eight tested scenarios.

## What this proves—and what it does not

It demonstrates basic Kafka producer/consumer integration, schema validation, per-key cycle ordering, target exclusion and measured local rates for 500-event batches. These rates are run-specific smoke-test measurements, not a formal throughput/latency benchmark. Phase 7 must run controlled repeated tests at multiple input rates and record resource usage and latency.

## Evidence

- `docs/project/phase2_matrix_results.csv`
- `docs/project/phase2_matrix_test.md`
- Local detailed logs: `results/phase2/matrix_<run-id>/` (ignored by Git)
