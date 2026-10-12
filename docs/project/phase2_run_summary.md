# Phase 2 — Kafka Telemetry Ingestion: Run Summary

Date: 2026-10-12
Status: Initial smoke test passed; full test matrix pending.

## Environment

- Kafka: 3.7.0
- ZooKeeper: 3.9.3
- Topic: cmapss-telemetry
- Partitions: 4
- Replication factor: 1
- Windows producer bootstrap: localhost:9092
- Docker-internal bootstrap: kafka:9093

## Producer Results

- Dataset: FD001
- Split: train
- Requested messages: 500
- Enqueued: 500
- Delivered: 500
- Failed deliveries: 0
- Outstanding after flush: 0
- Elapsed time: 5.03 seconds
- Achieved delivery rate: 99.47 messages/second
- RUL/target fields sent: No

A transient "Coordinator load in progress" warning appeared while the
producer was acquiring its idempotence PID. The producer retried and
the final delivery summary reported 500 successful deliveries.

## Consumer Results

- Messages read: 500
- Valid messages: 500
- Invalid messages/broker errors: 0
- Ordering warnings: 0
- Observed read rate: 93.38 messages/second

The consumer validated the first 500 messages from the topic. The
reported read rate is a measurement from this local run, not a
general scalability result.

## Schema and Topic Checks

- Event schema unit tests: 3 passed.
- Kafka topic verified with four partitions.
- No RUL or target labels included in telemetry.
- Sample events used the key format FD001_train_<engine_id>.

## Interpretation

The initial end-to-end Kafka smoke test passed: 500 telemetry events
were delivered, read and validated successfully.

This is not yet full Phase 2 completion. Remaining work includes
testing additional FD001-FD004 datasets and train/test inputs, checking
ordering across clean replays, and recording repeatable throughput
measurements.

## Evidence Files

- results/phase2/producer_fd001_500.txt
- results/phase2/consumer_fd001_500.txt
