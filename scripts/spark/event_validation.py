"""Pure-Python validation helpers shared by tests and the Spark job."""
from __future__ import annotations
import json
import math
from typing import Any

DATASETS = {"FD001", "FD002", "FD003", "FD004"}
SPLITS = {"train", "test"}
FORBIDDEN_TARGET_KEYS = {"rul", "remaining_useful_life", "target", "label", "y"}
SENSOR_FIELDS = [f"sensor_{i}" for i in range(1, 22)]
SETTING_FIELDS = ["setting_1", "setting_2", "setting_3"]
REQUIRED_FIELDS = {
    "schema_version", "dataset", "split", "engine_id", "cycle",
    *SETTING_FIELDS, *SENSOR_FIELDS,
}


def validate_payload(payload: str) -> list[str]:
    """Return validation errors for one Kafka JSON payload; [] means valid."""
    try:
        event: Any = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        return [f"invalid JSON: {exc}"]
    if not isinstance(event, dict):
        return ["event must be a JSON object"]

    errors: list[str] = []
    forbidden = FORBIDDEN_TARGET_KEYS.intersection(k.lower() for k in event)
    if forbidden:
        errors.append(f"target leakage fields are forbidden: {sorted(forbidden)}")
    missing = REQUIRED_FIELDS.difference(event)
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")
    if event.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if event.get("dataset") not in DATASETS:
        errors.append("dataset must be FD001, FD002, FD003 or FD004")
    if event.get("split") not in SPLITS:
        errors.append("split must be train or test")

    for field in ("engine_id", "cycle"):
        value = event.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            errors.append(f"{field} must be a positive integer")

    for field in [*SETTING_FIELDS, *SENSOR_FIELDS]:
        value = event.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{field} must be numeric")
        elif not math.isfinite(float(value)):
            errors.append(f"{field} must be finite")
    return errors
