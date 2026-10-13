import numpy as np
import pandas as pd
import pytest

from scripts.phase5.baseline_core import (
    calculate_metrics,
    capped_target,
    select_feature_columns,
    split_by_engine,
)


def sample_features(engine_count=10, cycles=4):
    rows = []
    for engine in range(1, engine_count + 1):
        for cycle in range(1, cycles + 1):
            row = {"engine_id": engine, "cycle": cycle, "setting_1": 0.1,
                   "setting_2": 0.2, "setting_3": 0.3, "RUL": cycles - cycle}
            for s in range(1, 22):
                row[f"sensor_{s}"] = float(s + cycle)
                for w in (15, 30):
                    for stat in ("mean", "std", "delta"):
                        row[f"sensor_{s}_w{w}_{stat}"] = float(s + cycle + w)
            rows.append(row)
    return pd.DataFrame(rows)


def test_window_feature_selection_excludes_identifiers_and_target():
    frame = sample_features()
    features15 = select_feature_columns(frame, 15)
    features30 = select_feature_columns(frame, 30)
    assert len(features15) == 87
    assert len(features30) == 87
    assert "engine_id" not in features15 and "cycle" not in features15 and "RUL" not in features15
    assert all("_w30_" not in col for col in features15)
    assert all("_w15_" not in col for col in features30)


def test_target_cap_and_uncapped_mode():
    frame = pd.DataFrame({"RUL": [0, 70, 125, 200]})
    assert capped_target(frame, 125).tolist() == [0, 70, 125, 125]
    assert capped_target(frame, None).tolist() == [0, 70, 125, 200]


def test_split_keeps_engines_disjoint():
    frame = sample_features(engine_count=20, cycles=3)
    train_idx, val_idx = split_by_engine(frame, validation_fraction=0.2, seed=42)
    train_ids = set(frame.iloc[train_idx].engine_id)
    val_ids = set(frame.iloc[val_idx].engine_id)
    assert train_ids.isdisjoint(val_ids)
    assert len(val_ids) == 4


def test_metrics_are_zero_for_perfect_predictions():
    scores = calculate_metrics([0, 10, 125], [0, 10, 125])
    assert scores["rmse"] == 0
    assert scores["mae"] == 0
    assert scores["nasa_score_sum"] == 0


def test_nasa_score_penalizes_rul_overprediction_more_for_same_error():
    truth = [50]
    underprediction = calculate_metrics(truth, [40])["nasa_score_sum"]
    overprediction = calculate_metrics(truth, [60])["nasa_score_sum"]
    assert overprediction > underprediction


def test_bad_window_is_rejected():
    with pytest.raises(ValueError):
        select_feature_columns(sample_features(), 20)
