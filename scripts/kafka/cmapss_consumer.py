"""Consume and validate DARE-RUL C-MAPSS telemetry events."""
from __future__ import annotations
import argparse
import json
import time
import uuid

TOPIC = "cmapss-telemetry"
REQUIRED = {"schema_version", "dataset", "split", "engine_id", "cycle", "setting_1", "setting_2", "setting_3"} | {f"sensor_{i}" for i in range(1, 22)}
FORBIDDEN = {"rul", "remaining_useful_life", "target", "label", "y"}


def validate_event(event: dict) -> list[str]:
    errors = []
    if not isinstance(event, dict):
        return ["payload is not a JSON object"]
    missing = REQUIRED - set(event)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
    leaked = FORBIDDEN.intersection(key.lower() for key in event)
    if leaked:
        errors.append(f"forbidden target fields: {sorted(leaked)}")
    if event.get("dataset") not in {"FD001", "FD002", "FD003", "FD004"}:
        errors.append("invalid dataset")
    if event.get("split") not in {"train", "test"}:
        errors.append("invalid split")
    try:
        if int(event.get("engine_id", 0)) < 1 or int(event.get("cycle", 0)) < 1:
            errors.append("engine_id and cycle must be positive")
    except (TypeError, ValueError):
        errors.append("engine_id and cycle must be integers")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default=TOPIC, help="Kafka topic to consume")
    parser.add_argument("--max-messages", type=int, default=20)
    parser.add_argument("--idle-timeout", type=float, default=15.0)
    args = parser.parse_args()
    if args.max_messages < 0 or args.idle_timeout <= 0:
        parser.error("--max-messages must be >= 0 and --idle-timeout must be > 0")

    try:
        from confluent_kafka import Consumer
    except ImportError:
        raise SystemExit("Missing Kafka client. Run: .\\.venv\\Scripts\\python.exe -m pip install -r .\\requirements-phase2.txt")

    consumer = Consumer({
        "bootstrap.servers": args.bootstrap_servers,
        "group.id": f"dare-rul-check-{uuid.uuid4().hex[:10]}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([args.topic])
    count = good = bad = ordering_warnings = 0
    last_cycle = {}
    first_message_at = time.perf_counter()
    last_message_at = first_message_at
    try:
        while args.max_messages == 0 or count < args.max_messages:
            msg = consumer.poll(1.0)
            now = time.perf_counter()
            if msg is None:
                if now - last_message_at >= args.idle_timeout:
                    break
                continue
            last_message_at = now
            count += 1
            if msg.error():
                bad += 1
                print(f"BROKER ERROR: {msg.error()}")
                continue
            key_bytes = msg.key()
            key = key_bytes.decode("utf-8", errors="replace") if key_bytes else "<no-key>"
            try:
                event = json.loads(msg.value().decode("utf-8"))
                errors = validate_event(event)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                event, errors = {}, [f"invalid JSON/UTF-8: {exc}"]
            if errors:
                bad += 1
                print(f"INVALID partition={msg.partition()} offset={msg.offset()} key={key}: {'; '.join(errors)}")
                continue
            good += 1
            engine_key = key
            cycle = int(event["cycle"])
            if engine_key in last_cycle and cycle <= last_cycle[engine_key]:
                ordering_warnings += 1
                print(f"ORDER WARNING key={key}: cycle {last_cycle[engine_key]} -> {cycle}")
            last_cycle[engine_key] = cycle
            if count <= 5:
                print(f"OK partition={msg.partition()} offset={msg.offset()} key={key} cycle={cycle} sensor_1={event['sensor_1']}")
        try:
            consumer.commit(asynchronous=False)
        except Exception as exc:  # best-effort commit for this disposable inspection group
            print(f"Note: offset commit skipped: {exc}")
    except KeyboardInterrupt:
        print("Consumer interrupted by user.")
    finally:
        consumer.close()
    elapsed = max(time.perf_counter() - first_message_at, 1e-9)
    print("DARE-RUL Kafka consumer summary")
    print(f"Topic: {args.topic}")
    print(f"Read: {count}; valid: {good}; invalid/broker errors: {bad}; ordering warnings: {ordering_warnings}")
    print(f"Observed read rate: {count / elapsed:.2f} messages/sec")
    print("Note: ordering warnings can occur if a topic contains multiple complete replays. Use a fresh topic for a clean first replay test.")
    return 1 if bad or ordering_warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
