import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

from scripts.phase5.baseline_core import SENSOR_COLUMNS, SETTING_COLUMNS
from scripts.phase6.ensemble_core import EXPERTS
from scripts.phase7.phase7_core import (
    cross_window_features,
    enhanced_context,
    gate_expected_errors,
    meta_features,
    multiresolution_context,
    perturb_sensor_context,
    permutable_feature_groups,
)


def synthetic_phase4(rows=8):
    data = {
        "engine_id": np.repeat([1, 2], rows // 2),
        "cycle": list(range(1, rows // 2 + 1)) * 2,
        "RUL": np.arange(rows, 0, -1, dtype=float),
    }
    for j, col in enumerate(SETTING_COLUMNS):
        data[col] = np.linspace(0.1, 1.1, rows) + j
    for i, col in enumerate(SENSOR_COLUMNS, start=1):
        current = np.linspace(i, i + 1.0, rows)
        data[col] = current
        for w in (15, 30):
            data[f"{col}_w{w}_mean"] = current - (w / 100.0)
            data[f"{col}_w{w}_std"] = np.linspace(0.1, 0.2, rows) + i / 100.0
            data[f"{col}_w{w}_delta"] = np.linspace(0, 1, rows) * (w / 10.0)
    return pd.DataFrame(data)


def pred_frame(n):
    return pd.DataFrame({name: np.linspace(i + 1, i + n, n) for i, name in enumerate(EXPERTS)})


def test_multires_context_has_both_windows_and_excludes_id_cycle_target():
    frame = synthetic_phase4()
    ctx = multiresolution_context(frame)
    assert "sensor_1_w15_mean" in ctx
    assert "sensor_1_w30_mean" in ctx
    assert not {"engine_id", "cycle", "RUL"}.intersection(ctx.columns)
    assert ctx.shape[1] == 150


def test_cross_window_context_adds_84_finite_features():
    frame = synthetic_phase4()
    base = multiresolution_context(frame)
    derived = cross_window_features(base)
    assert derived.shape == (len(frame), 84)
    assert "derived_sensor_1_mean_contrast_15_30" in derived.columns
    assert "derived_sensor_21_current_zscore_w30" in derived.columns
    assert np.isfinite(derived.to_numpy()).all()
    all_features = enhanced_context(frame, add_cross_window=True)
    assert all_features.shape[1] == 234


def test_meta_features_include_or_omit_disagreement_group():
    frame = synthetic_phase4()
    context = enhanced_context(frame)
    preds = pred_frame(len(frame))
    with_disagreement = meta_features(context, preds, include_disagreement=True)
    without_disagreement = meta_features(context, preds, include_disagreement=False)
    assert "expert_spread" in with_disagreement.columns
    assert "abs_deviation_RF15" in with_disagreement.columns
    assert "expert_spread" not in without_disagreement.columns
    assert all(f"pred_{e}" in without_disagreement.columns for e in EXPERTS)
    assert not {"engine_id", "cycle", "RUL"}.intersection(with_disagreement.columns)


def test_meta_features_reject_target_or_mismatched_rows():
    context = pd.DataFrame({"sensor_1": [1.0], "RUL": [2.0]})
    with pytest.raises(ValueError):
        meta_features(context, pred_frame(1))
    context = pd.DataFrame({"sensor_1": [1.0, 2.0]})
    with pytest.raises(ValueError):
        meta_features(context, pred_frame(1))


def test_sensor_feature_perturbation_is_reproducible_and_leaves_settings_alone():
    frame = synthetic_phase4()
    ctx = multiresolution_context(frame)
    perturbed1 = perturb_sensor_context(ctx, ctx, 0.05, seed=42)
    perturbed2 = perturb_sensor_context(ctx, ctx, 0.05, seed=42)
    pd.testing.assert_frame_equal(perturbed1, perturbed2)
    pd.testing.assert_series_equal(perturbed1["setting_1"], ctx["setting_1"])
    assert not np.allclose(perturbed1["sensor_1"], ctx["sensor_1"])
    pd.testing.assert_frame_equal(perturb_sensor_context(ctx, ctx, 0.0, seed=1), ctx)


def test_feature_groups_are_disjoint_and_cover_meta_columns():
    frame = synthetic_phase4()
    x = meta_features(enhanced_context(frame), pred_frame(len(frame)), include_disagreement=True)
    groups = permutable_feature_groups(x)
    flat = [col for cols in groups.values() for col in cols]
    assert len(flat) == len(set(flat))
    assert set(flat) == set(x.columns)
    assert "cross_window_engineered" in groups
    assert "expert_disagreement" in groups


def test_gate_expected_errors_returns_finite_nonnegative_predictions():
    frame = synthetic_phase4()
    x = meta_features(enhanced_context(frame), pred_frame(len(frame)), include_disagreement=True)
    gates = {}
    for expert in EXPERTS:
        gate = DummyRegressor(strategy="constant", constant=2.5).fit(x, np.full(len(x), 2.5))
        gates[expert] = gate
    errors = gate_expected_errors(gates, x)
    assert list(errors.columns) == list(EXPERTS)
    assert errors.shape == (len(frame), len(EXPERTS))
    assert np.allclose(errors.to_numpy(), 2.5)


def test_group_permutation_helpers_handle_empty_group_safely():
    frame = synthetic_phase4()
    x = meta_features(multiresolution_context(frame), pred_frame(len(frame)), include_disagreement=False)
    groups = permutable_feature_groups(x)
    assert "expert_predictions" in groups
    assert "expert_disagreement" not in groups
