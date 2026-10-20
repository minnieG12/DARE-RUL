from pathlib import Path

import pandas as pd
import pytest

from dashboard.data import load_phase8_artifacts, filtered_fleet


def _write_artifacts(root: Path):
    folder = root / "results" / "phase8"
    folder.mkdir(parents=True)
    base = {
        "subset": "FD001", "engine_id": 1, "final_cycle": 100,
        "selected_method": "cross_window_error_gate", "training_rul_cap": 125,
        "predicted_rul": 20.0, "pred_RF15": 21.0, "pred_HGB15": 19.0,
        "pred_RF30": 22.0, "pred_HGB30": 18.0,
        "expected_error_RF15": 2.0, "expected_error_HGB15": 1.0,
        "expected_error_RF30": 3.0, "expected_error_HGB30": 4.0,
        "weight_RF15": .2, "weight_HGB15": .3, "weight_RF30": .2, "weight_HGB30": .3,
    }
    predictions = pd.DataFrame([base])
    scored = predictions.assign(RUL_true=22.0, error_pred_minus_true=-2.0, absolute_error=2.0)
    metrics = pd.DataFrame([{
        "subset": s, "selected_method": "x", "test_engines": 1,
        "rmse": 1.0, "mae": 1.0, "nasa_score_sum": 1.0, "nasa_score_mean": 1.0,
    } for s in ("FD001", "FD002", "FD003", "FD004")])
    maintenance = predictions.assign(risk_tier="HIGH", illustrative_next_step="demo only")
    predictions.to_csv(folder / "test_predictions.csv", index=False)
    scored.to_csv(folder / "test_scored_predictions.csv", index=False)
    metrics.to_csv(folder / "final_test_metrics.csv", index=False)
    maintenance.to_csv(folder / "maintenance_recommendations.csv", index=False)


def test_load_phase8_artifacts_and_filter(tmp_path):
    _write_artifacts(tmp_path)
    artifacts = load_phase8_artifacts(tmp_path)
    view = filtered_fleet(artifacts, ["FD001"], ["HIGH"], "1")
    assert len(view) == 1
    assert view.iloc[0]["predicted_rul"] == 20.0


def test_load_artifacts_rejects_missing_schema(tmp_path):
    _write_artifacts(tmp_path)
    path = tmp_path / "results" / "phase8" / "test_predictions.csv"
    pd.DataFrame([{"subset": "FD001"}]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_phase8_artifacts(tmp_path)
