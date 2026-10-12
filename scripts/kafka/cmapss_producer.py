"""Replay C-MAPSS train/test rows to Kafka as target-free telemetry JSON."""
from __future__ import annotations
import argparse
import json
import re
import time
from pathlib import Path
from typing import Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "CMAPSSData"
TOPIC = "cmapss-telemetry"
COLUMNS = ["engine_id", "cycle", "setting_1", "setting_2", "setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
FORBIDDEN_TARGET_KEYS = {"rul", "remaining_useful_life", "target", "label", "y"}


def build_event(dataset: str, split: str, row: Sequence[float]) -> dict:
    """Convert one 26-value C-MAPSS row to a JSON-safe, target-free event."""
    if len(row) != 26:
        raise ValueError(f"Expected 26 values (ID, cycle, 3 settings, 21 sensors); got {len(row)}")
    values = [float(x) for x in row]
    if any(pd.isna(x) or not (-float("inf") < x < float("inf")) for x in values):
        raise ValueError("Row contains a missing or non-finite value")
    engine_id, cycle = int(values[0]), int(values[1])
    if engine_id < 1 or cycle < 1:
        raise ValueError("engine_id and cycle must be positive integers")
    event = {
        "schema_version": 1,
        "dataset": dataset,
        "split": split,
        "engine_id": engine_id,
        "cycle": cycle,
        "setting_1": values[2],
        "setting_2": values[3],
        "setting_3": values[4],
    }
    for index in range(1, 22):
        event[f"sensor_{index}"] = values[4 + index]
    if FORBIDDEN_TARGET_KEYS.intersection(k.lower() for k in event):
        raise AssertionError("Target leakage: an RUL/target field was included")
    return event


def load_rows(dataset: str, split: str) -> pd.DataFrame:
    path = RAW_DIR / f"{split}_{dataset}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Missing input data: {path}")
    frame = pd.read_csv(path, sep=r"\s+", header=None, names=COLUMNS, engine="python")
    if frame.shape[1] != 26 or frame.isna().any().any():
        raise ValueError(f"Unexpected schema or missing values in {path.name}")
    frame = frame.sort_values(["engine_id", "cycle"], kind="mergesort").reset_index(drop=True)
    if frame.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"Duplicate engine-cycle row in {path.name}")
    for engine_id, group in frame.groupby("engine_id", sort=False):
        if not group["cycle"].is_monotonic_increasing:
            raise ValueError(f"Cycles are not increasing for engine {engine_id} in {path.name}")
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["FD001", "FD002", "FD003", "FD004"], default="FD001")
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--rate", type=float, default=100.0, help="Target messages/second; 0 disables pacing")
    parser.add_argument("--max-messages", type=int, default=0, help="0 sends all rows; use 500 for the first demo")
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default=TOPIC, help="Kafka topic for this replay")
    args = parser.parse_args()
    if args.rate < 0 or args.max_messages < 0:
        parser.error("--rate and --max-messages cannot be negative")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", args.topic) or args.topic in {".", ".."}:
        parser.error("--topic must be a valid Kafka topic name (letters, numbers, dot, underscore, hyphen)")

    try:
        from confluent_kafka import Producer
    except ImportError:
        raise SystemExit("Missing Kafka client. Run: .\\.venv\\Scripts\\python.exe -m pip install -r .\\requirements-phase2.txt")

    frame = load_rows(args.dataset, args.split)
    if args.max_messages:
        frame = frame.iloc[:args.max_messages]
    total_to_send = len(frame)
    if total_to_send == 0:
        raise SystemExit("No rows selected for replay")

    delivered = 0
    failed = 0

    def delivery_callback(error, message):
        nonlocal delivered, failed
        if error is not None:
            failed += 1
        else:
            delivered += 1

    producer = Producer({
        "bootstrap.servers": args.bootstrap_servers,
        "client.id": "dare-rul-cmapss-producer",
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "lz4",
        "message.timeout.ms": 120000,
    })
    start = time.perf_counter()
    accepted = 0
    try:
        for index, values in enumerate(frame.itertuples(index=False, name=None)):
            event = build_event(args.dataset, args.split, values)
            key = f"{args.dataset}_{args.split}_{event['engine_id']}"
            payload = json.dumps(event, separators=(",", ":"), allow_nan=False)
            while True:
                try:
                    producer.produce(args.topic, key=key.encode("utf-8"), value=payload.encode("utf-8"), on_delivery=delivery_callback)
                    accepted += 1
                    producer.poll(0)
                    break
                except BufferError:
                    producer.poll(0.1)
            if args.rate > 0:
                deadline = start + (index + 1) / args.rate
                delay = deadline - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
        outstanding = producer.flush(120)
    finally:
        # flush above triggers delivery callbacks; close is not required by confluent-kafka Producer.
        pass
    elapsed = time.perf_counter() - start
    achieved = delivered / elapsed if elapsed > 0 else 0.0
    print("DARE-RUL Kafka producer summary")
    print(f"Dataset/split: {args.dataset}/{args.split}")
    print(f"Topic: {args.topic}; bootstrap: {args.bootstrap_servers}")
    print(f"Rows selected / messages enqueued: {total_to_send} / {accepted}")
    print(f"Delivered: {delivered}; failed: {failed}; outstanding after flush: {outstanding}")
    print(f"Elapsed seconds: {elapsed:.2f}; achieved delivery rate: {achieved:.2f} messages/sec")
    print("RUL/target fields sent: NO")
    return 1 if failed or outstanding else 0


if __name__ == "__main__":
    raise SystemExit(main())
