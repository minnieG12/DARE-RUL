# Phase 2 scope — Kafka telemetry ingestion

## Purpose

Replay NASA C-MAPSS sensor rows as controlled JSON events through Kafka. This simulates a stream from historical data; it is not live aircraft telemetry.

## Payload contract

One message per engine-cycle. Fields: `schema_version`, `dataset`, `split`, `engine_id`, `cycle`, `setting_1`–`setting_3`, `sensor_1`–`sensor_21`. No `RUL`, `target`, `label` or future-derived target fields.

## Partitioning

Message key: `<dataset>_<split>_<engine_id>`, for example `FD001_train_1`. Kafka's keyed partitioning keeps each engine's events in the same partition (assuming the same topic and consistent producer partitioner), preserving the within-partition order for that key.

## Initial demo

- One local Kafka broker + ZooKeeper in Docker Compose.
- Topic `cmapss-telemetry`, 4 partitions, replication factor 1 (local development only).
- Replay 500 FD001 training events at a target rate of 100 events/sec.
- Consumer reads a limited sample and checks schema, missing fields, forbidden targets and cycle order.
- Save output logs/results before claiming Phase 2 complete.

## Exit criteria

- Broker reachable from host via `localhost:9092`.
- Topic exists with 4 partitions.
- Producer reports delivered/error counts and elapsed time/rate.
- Consumer validates messages and prints partition/offset/key.
- No RUL target field is in payload.
- Ordering check passes for a fresh topic/replay.
- Document command, workload, partition count, observed throughput and limitations.
