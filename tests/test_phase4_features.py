import numpy as np
import pandas as pd
import pytest

from scripts.features.build_phase4_features import (
    ALL_COLUMNS,
    SENSOR_COLUMNS,
    add_temporal_features,
    make_train_features,
    make_test_features,
    read_rul_targets,
    validate_cycles,
)


def toy_rows():
    rows = []
    # Two engines with distinctly different sensor values ensure no cross-engine bleed.
    for engine, values in [(1, [10.0, 20.0, 30.0]), (2, [100.0, 200.0])]:
        for cycle, value in enumerate(values, start=1):
            rows.append([engine, cycle, 0.1, 0.2, 0.3] + [value] * 21)
    return pd.DataFrame(rows, columns=ALL_COLUMNS)


def test_temporal_features_do_not_mix_engines_and_are_past_only():
    raw = toy_rows()
    features = add_temporal_features(raw, windows=(2,))
    engine1_cycle2 = features.query("engine_id == 1 and cycle == 2").iloc[0]
    engine2_cycle1 = features.query("engine_id == 2 and cycle == 1").iloc[0]
    assert engine1_cycle2["sensor_1_w2_mean"] == pytest.approx(15.0)
    assert engine2_cycle1["sensor_1_w2_mean"] == pytest.approx(100.0)
    assert engine2_cycle1["sensor_1_w2_delta"] == pytest.approx(0.0)


def test_training_rul_is_remaining_cycles_and_cap_is_optional():
    raw = toy_rows()
    uncapped = make_train_features(raw, windows=(2,))
    eng1 = uncapped.query("engine_id == 1").sort_values("cycle")
    assert eng1["RUL"].tolist() == [2, 1, 0]
    capped = make_train_features(raw, windows=(2,), rul_cap=1)
    eng1_capped = capped.query("engine_id == 1").sort_values("cycle")
    assert eng1_capped["RUL"].tolist() == [1, 1, 0]


def test_test_features_keep_all_trajectory_and_one_final_row_per_engine():
    raw = toy_rows()
    trajectory, final = make_test_features(raw, windows=(2,))
    assert len(trajectory) == 5
    assert len(final) == 2
    assert final.sort_values("engine_id")["cycle"].tolist() == [3, 2]
    assert "RUL" not in trajectory.columns
    assert "RUL" not in final.columns


def test_duplicate_engine_cycle_is_rejected():
    raw = toy_rows()
    raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_cycles(raw)


def test_rul_count_must_match_test_engine_count(tmp_path):
    target_path = tmp_path / "RUL_FD001.txt"
    target_path.write_text("7\n8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="has 2 targets but test file has 3 engines"):
        read_rul_targets(target_path, [1, 2, 3])
