import numpy as np
import pandas as pd
import pytest

from scripts.phase9.ensemble_v2 import EXPERTS, blend_v2

STATIC = {"RF15": 0.25, "HGB15": 0.25, "RF30": 0.25, "HGB30": 0.25}


def test_v2_weights_sum_to_one_and_respect_cap():
    pred = pd.DataFrame({name: [10.0, 20.0] for name in EXPERTS})
    err = pd.DataFrame({"RF15": [0.1, 100.0], "HGB15": [20.0, 0.2], "RF30": [30.0, 30.0], "HGB30": [40.0, 40.0]})
    y, weights, fallback = blend_v2(pred, err, STATIC, max_weight=0.60, shrinkage=0.20)
    matrix = weights.to_numpy()
    assert np.isfinite(y).all()
    assert np.allclose(matrix.sum(axis=1), 1.0)
    assert matrix.max() <= 0.60 + 1e-8
    assert fallback.eq("").all()


def test_v2_invalid_error_row_uses_static_fallback():
    pred = pd.DataFrame({name: [10.0, 20.0] for name in EXPERTS})
    err = pd.DataFrame({name: [1.0, 1.0] for name in EXPERTS})
    err.loc[1, "HGB15"] = np.nan
    y, weights, fallback = blend_v2(pred, err, STATIC)
    assert fallback.tolist() == ["", "non_finite_expected_error"]
    assert np.allclose(weights.iloc[1].to_numpy(), np.array([0.25] * 4))
    assert np.isfinite(y).all()


def test_v2_rejects_nonfinite_expert_predictions():
    pred = pd.DataFrame({name: [10.0] for name in EXPERTS})
    pred.loc[0, "RF15"] = np.inf
    err = pd.DataFrame({name: [1.0] for name in EXPERTS})
    with pytest.raises(ValueError, match="Expert predictions must be finite"):
        blend_v2(pred, err, STATIC)


def test_v2_rejects_bad_static_weight_contract():
    pred = pd.DataFrame({name: [10.0] for name in EXPERTS})
    err = pd.DataFrame({name: [1.0] for name in EXPERTS})
    with pytest.raises(ValueError):
        blend_v2(pred, err, {"RF15": 1.0})


def test_v2_clips_final_rul_to_configured_cap():
    pred = pd.DataFrame({"RF15": [200.0], "HGB15": [200.0], "RF30": [200.0], "HGB30": [200.0]})
    err = pd.DataFrame({name: [1.0] for name in EXPERTS})
    result, _, _ = blend_v2(pred, err, STATIC, rul_cap=125)
    assert result.tolist() == [125.0]
