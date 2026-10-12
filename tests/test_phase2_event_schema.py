from scripts.kafka.cmapss_producer import build_event
from scripts.kafka.cmapss_consumer import validate_event


def sample_row():
    return [1, 7, 0.1, 0.2, 0.3] + [float(i) for i in range(1, 22)]


def test_event_contains_all_expected_sensor_fields_and_no_target():
    event = build_event("FD001", "train", sample_row())
    assert event["engine_id"] == 1
    assert event["cycle"] == 7
    assert event["sensor_1"] == 1.0
    assert event["sensor_21"] == 21.0
    assert not ({"rul", "target", "label"} & {k.lower() for k in event})
    assert validate_event(event) == []


def test_consumer_rejects_a_target_leak():
    event = build_event("FD001", "train", sample_row())
    event["RUL"] = 5
    assert any("forbidden target fields" in error for error in validate_event(event))


def test_producer_rejects_bad_row_width():
    try:
        build_event("FD001", "train", [1, 1])
    except ValueError as error:
        assert "26 values" in str(error)
    else:
        raise AssertionError("Expected bad row width to fail")
