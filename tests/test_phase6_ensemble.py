import numpy as np
import pandas as pd
import pytest

from scripts.phase6.ensemble_core import (
    EXPERTS,
    adaptive_blend,
    build_validation_error_artifact,
    engine_balanced_sample_weights,
    engine_macro_metrics,
    inverse_error_weights,
    make_gate_features,
    metric_summary,
    static_inverse_mae_weights,
)


def test_inverse_error_weights_normalize_and_prefer_lower_error():
    weights = inverse_error_weights({"RF15": 10, "HGB15": 5, "RF30": 20, "HGB30": 2})
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["HGB30"] > weights["HGB15"] > weights["RF15"] > weights["RF30"]


def test_inverse_error_weights_reject_invalid_input():
    with pytest.raises(ValueError):
        inverse_error_weights({"RF15": -1, "HGB15": 2, "RF30": 3, "HGB30": 4})


def test_gate_features_exclude_identifiers_and_add_disagreement():
    context = pd.DataFrame({"setting_1": [1.0, 2.0], "sensor_1_w30_mean": [3.0, 4.0]})
    preds = pd.DataFrame({expert: [float(i), float(i + 1)] for i, expert in enumerate(EXPERTS, start=10)})
    features = make_gate_features(context, preds)
    assert "engine_id" not in features and "cycle" not in features and "RUL" not in features
    assert "expert_spread" in features and "expert_range" in features
    assert all(f"abs_deviation_{name}" in features for name in EXPERTS)


def test_gate_features_refuse_identifier_leakage():
    context = pd.DataFrame({"engine_id": [1], "sensor_1_w30_mean": [1.0]})
    preds = pd.DataFrame({expert: [1.0] for expert in EXPERTS})
    with pytest.raises(ValueError):
        make_gate_features(context, preds)


def test_adaptive_blend_weights_sum_to_one_and_react_to_errors():
    pred = pd.DataFrame({"RF15": [10, 10], "HGB15": [20, 20], "RF30": [30, 30], "HGB30": [40, 40]})
    errors = pd.DataFrame({"RF15": [1, 100], "HGB15": [10, 1], "RF30": [10, 10], "HGB30": [20, 20]})
    blended, weights = adaptive_blend(pred, errors)
    assert len(blended) == 2
    assert weights.iloc[0].sum() == pytest.approx(1.0)
    assert weights.iloc[1].sum() == pytest.approx(1.0)
    assert weights.loc[0, "weight_RF15"] > weights.loc[1, "weight_RF15"]
    assert weights.loc[1, "weight_HGB15"] > weights.loc[0, "weight_HGB15"]


def test_engine_balanced_weights_give_each_engine_equal_total_weight():
    engine_ids = [1, 1, 1, 2, 3, 3]
    weights = engine_balanced_sample_weights(engine_ids)
    totals = pd.DataFrame({"engine": engine_ids, "weight": weights}).groupby("engine").weight.sum()
    assert np.allclose(totals.to_numpy(), np.ones(3))


def test_metrics_and_engine_macro_metrics_are_finite():
    y = [10, 12, 8, 30, 25]
    p = [11, 10, 8, 32, 24]
    row_metrics = metric_summary(y, p)
    macro = engine_macro_metrics([1, 1, 2, 3, 3], y, p)
    assert row_metrics["rmse"] >= 0 and row_metrics["mae"] >= 0
    assert macro["engine_macro_rmse"] >= 0
    assert np.isfinite(list(row_metrics.values())).all()


def test_static_weights_same_contract_as_dynamic_weight_helper():
    weights = static_inverse_mae_weights({"RF15": 10, "HGB15": 5, "RF30": 8, "HGB30": 4})
    assert set(weights) == set(EXPERTS)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_validation_error_artifact_uses_validation_keys_not_oof_keys():
    # Validation can have fewer rows than OOF training predictions; its own
    # engine/cycle keys must align one-to-one with gate outputs.
    validation_keys = pd.DataFrame({
        "engine_id": [101, 101, 104],
        "cycle": [8, 9, 3],
    })
    expected_errors = pd.DataFrame({name: [1.0, 2.0, 3.0] for name in EXPERTS})
    artifact = build_validation_error_artifact("FD001", validation_keys, expected_errors)
    assert len(artifact) == len(validation_keys)
    assert artifact["engine_id"].tolist() == [101, 101, 104]
    assert artifact["cycle"].tolist() == [8, 9, 3]
    assert artifact["subset"].unique().tolist() == ["FD001"]
    assert all(f"expected_error_{name}" in artifact for name in EXPERTS)


def test_validation_error_artifact_rejects_mismatched_lengths():
    validation_keys = pd.DataFrame({"engine_id": [1, 1], "cycle": [3, 4]})
    expected_errors = pd.DataFrame({name: [1.0] for name in EXPERTS})
    with pytest.raises(ValueError, match="equal length"):
        build_validation_error_artifact("FD001", validation_keys, expected_errors)
