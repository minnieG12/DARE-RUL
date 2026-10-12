import json
from scripts.spark.event_validation import validate_payload


def valid_event():
    event = {
        "schema_version": 1,
        "dataset": "FD001",
        "split": "train",
        "engine_id": 1,
        "cycle": 1,
        "setting_1": 0.0,
        "setting_2": 0.0,
        "setting_3": 0.0,
    }
    event.update({f"sensor_{i}": float(i) for i in range(1, 22)})
    return event


def test_valid_sensor_event_passes():
    assert validate_payload(json.dumps(valid_event())) == []


def test_target_leakage_is_rejected():
    event = valid_event()
    event["rul"] = 100
    assert any("target leakage" in error for error in validate_payload(json.dumps(event)))


def test_missing_sensor_is_rejected():
    event = valid_event()
    del event["sensor_10"]
    errors = validate_payload(json.dumps(event))
    assert any("missing required fields" in error for error in errors)


def test_non_finite_sensor_is_rejected():
    event = valid_event()
    event["sensor_3"] = float("inf")
    assert any("must be finite" in error for error in validate_payload(json.dumps(event)))


def test_malformed_json_is_rejected():
    assert any("invalid JSON" in error for error in validate_payload("{not-json"))
