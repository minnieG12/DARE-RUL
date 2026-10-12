# Phase 2 — Kafka Telemetry Ingestion: Initial Run Record

Date: 2026-10-12
Status: Producer smoke test passed; first consumer read requires isolated re-test.

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
- Messages enqueued: 500
- Delivered: 500
- Failed deliveries: 0
- Outstanding after flush: 0
- Elapsed time: 5.03 seconds
- Achieved delivery rate: 99.47 messages/second
- RUL/target fields sent: No

A transient `Coordinator load in progress` warning appeared during producer initialization. The producer retried and reported successful delivery of all 500 messages.

## Consumer Results

- Messages read: 500
- Valid messages: 500
- Invalid messages/broker errors: 0
- Ordering warnings: 0
- Observed read rate: 93.38 messages/second

## Important qualification

The consumer used a fresh consumer group with `auto.offset.reset=earliest` against the shared `cmapss-telemetry` topic. The first displayed key in the consumer log was `FD001_train_2`, cycle 1. Because the standard FD001 training file starts with engine 1, the topic may have contained earlier records from a prior run. Therefore, these logs separately establish (a) that 500 messages were delivered by the producer and (b) that 500 topic messages were valid, but they do not conclusively prove the consumer read the exact batch produced in this run.

The Phase 2 Completion Matrix fixes this by creating a unique, empty topic per dataset/split scenario. Do not use this initial shared-topic run alone as evidence of a fully correlated end-to-end test.

## Other Checks

- Event schema unit tests: 3 passed.
- Topic verified with four partitions.
- No RUL/target fields included in telemetry.

## Evidence Files

- `results/phase2/producer_fd001_500.txt`
- `results/phase2/consumer_fd001_500.txt`
