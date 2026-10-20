from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.phase8.run_phase8 import FINAL_VARIANTS, fit_oof_experts, validate_test_predictor_schema
from scripts.phase8.maintenance_demo import recommendation_for_rul
from scripts.phase5.baseline_core import calculate_metrics, select_feature_columns


def test_final_variant_selection_is_frozen_and_complete():
    assert FINAL_VARIANTS == {
        "FD001": "cross_window_no_disagreement",
        "FD002": "cross_window_error_gate",
        "FD003": "cross_window_error_gate",
        "FD004": "cross_window_no_disagreement",
    }


def test_metrics_match_expected_values():
    got = calculate_metrics([10, 20], [12, 17])
    assert got["rmse"] == pytest.approx(np.sqrt(6.5))
    assert got["mae"] == pytest.approx(2.5)
    assert got["nasa_score_sum"] > 0
    assert got["nasa_score_mean"] == pytest.approx(got["nasa_score_sum"] / 2)


def test_oof_fit_rejects_too_many_folds():
    rows = []
    for engine_id in range(1, 5):
        for cycle in range(1, 3):
            row = {"engine_id": engine_id, "cycle": cycle, "RUL": 2 - cycle,
                   "setting_1": 0.1, "setting_2": 0.2, "setting_3": 0.3}
            for sensor_id in range(1, 22):
                row[f"sensor_{sensor_id}"] = float(sensor_id + cycle)
                for window in (15, 30):
                    row[f"sensor_{sensor_id}_w{window}_mean"] = float(sensor_id + cycle)
                    row[f"sensor_{sensor_id}_w{window}_std"] = 0.1
                    row[f"sensor_{sensor_id}_w{window}_delta"] = 0.0
            rows.append(row)
    train = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="oof-folds must be between"):
        fit_oof_experts(train, "FD001", rul_cap=125, folds=5, seed=42)


def test_test_predictor_schema_rejects_rul_target():
    frame = pd.DataFrame({"engine_id": [1], "cycle": [10], "setting_1": [0.1], "setting_2": [0.2],
                          "setting_3": [0.3], "RUL": [99]})
    with pytest.raises(ValueError, match="target columns"):
        validate_test_predictor_schema(frame, "FD001")


def test_model_features_exclude_ids_and_rul():
    row = {"engine_id": 1, "cycle": 10, "RUL": 0, "setting_1": 0.1, "setting_2": 0.2, "setting_3": 0.3}
    for sensor_id in range(1, 22):
        row[f"sensor_{sensor_id}"] = float(sensor_id)
        for window in (15, 30):
            row[f"sensor_{sensor_id}_w{window}_mean"] = float(sensor_id)
            row[f"sensor_{sensor_id}_w{window}_std"] = 0.1
            row[f"sensor_{sensor_id}_w{window}_delta"] = 0.0
    frame = pd.DataFrame([row])
    for window in (15, 30):
        cols = select_feature_columns(frame, window)
        assert "RUL" not in cols
        assert "engine_id" not in cols
        assert "cycle" not in cols


def test_risk_bands_and_boundaries():
    assert recommendation_for_rul(10)[0] == "CRITICAL"
    assert recommendation_for_rul(10.1)[0] == "HIGH"
    assert recommendation_for_rul(30)[0] == "HIGH"
    assert recommendation_for_rul(30.1)[0] == "MONITOR"


def test_risk_bands_reject_invalid_values():
    with pytest.raises(ValueError):
        recommendation_for_rul(-1)
    with pytest.raises(ValueError):
        recommendation_for_rul(5, critical_threshold=10, high_threshold=10)
