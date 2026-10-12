# DARE-RUL Phase 2 — Kafka telemetry ingestion

Extract this ZIP into `E:\Projects\big data\DARE-RUL`. It adds new files only; it does not include or modify `data\CMAPSSData`.

## Install the Kafka client

```powershell
cd "E:\Projects\big data\DARE-RUL"
.\.venv\Scripts\python.exe -m pip install -r .\requirements-phase2.txt
.\.venv\Scripts\python.exe -m pip freeze | Set-Content -Encoding utf8 .\requirements-lock.txt
```

## Start Kafka and create the topic

```powershell
.\scripts\kafka\start_kafka.ps1
.\scripts\kafka\create_topic.ps1
.\scripts\kafka\verify_kafka.ps1
```

Topic details: `cmapss-telemetry`, 4 partitions, replication factor 1 for local single-broker development.

## Test the event format, then replay 500 messages

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_phase2_event_schema.py -q
.\.venv\Scripts\python.exe .\scripts\kafka\cmapss_producer.py --dataset FD001 --split train --rate 100 --max-messages 500
.\.venv\Scripts\python.exe .\scripts\kafka\cmapss_consumer.py --max-messages 500
```

The producer creates one JSON event per row and never sends an RUL target. `FD001_train_1` is an example message key; it keeps the engine's events on the same partition. The rate is a target pace, not a guarantee.

## What success looks like

- Compose shows both Kafka and ZooKeeper running.
- Topic description reports 4 partitions.
- Unit tests say `3 passed`.
- Producer shows delivered messages, errors, elapsed seconds and measured delivery rate.
- Consumer shows valid JSON events with partition/offset/key, no forbidden target fields and no ordering warnings on a fresh topic.

This is historical C-MAPSS replay, not real aircraft telemetry. Run `stop_kafka.ps1` to stop the containers while preserving their named volumes. Avoid `docker compose down --volumes` unless you intentionally want to delete Kafka data.
