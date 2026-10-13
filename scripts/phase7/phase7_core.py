"""Reusable Phase 7 utilities for enhanced multi-resolution ensemble context."""
from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from scripts.phase5.baseline_core import select_feature_columns
from scripts.phase6.ensemble_core import EXPERTS, adaptive_blend

EPS = 1e-3


def multiresolution_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Select the original settings/sensors plus both 15- and 30-cycle summaries.

    Never includes engine_id, cycle, or RUL. Those columns may be present in
    ``frame`` but are strictly join/target columns rather than predictors.
    """
    cols = list(dict.fromkeys(select_feature_columns(frame, 15) + select_feature_columns(frame, 30)))
    forbidden = {"engine_id", "cycle", "RUL", "RUL_true_capped"}
    if forbidden.intersection(cols):
        raise AssertionError("Identifier or target entered the context feature list")
    context = frame.loc[:, cols].reset_index(drop=True).copy()
    numeric = context.to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Multi-resolution context contains non-finite values")
    return context


def cross_window_features(context: pd.DataFrame) -> pd.DataFrame:
    """Build causal contrasts from existing trailing 15/30-cycle features.

    These features are computed from Phase 4's current/past-only window summaries;
    they do not use future cycles or RUL labels.
    Per sensor: short-vs-long mean contrast, short-vs-long variability ratio,
    short-vs-long delta contrast, and current reading standardized against the
    30-cycle mean/std (84 features total for 21 sensors).
    """
    required: list[str] = []
    for i in range(1, 22):
        required.extend([
            f"sensor_{i}",
            f"sensor_{i}_w15_mean", f"sensor_{i}_w15_std", f"sensor_{i}_w15_delta",
            f"sensor_{i}_w30_mean", f"sensor_{i}_w30_std", f"sensor_{i}_w30_delta",
        ])
    missing = [col for col in required if col not in context.columns]
    if missing:
        raise ValueError(f"Cannot build cross-window features; missing columns: {missing[:8]}")

    new: dict[str, np.ndarray] = {}
    for i in range(1, 22):
        sensor = f"sensor_{i}"
        m15, s15, d15 = (context[f"{sensor}_w15_mean"], context[f"{sensor}_w15_std"], context[f"{sensor}_w15_delta"])
        m30, s30, d30 = (context[f"{sensor}_w30_mean"], context[f"{sensor}_w30_std"], context[f"{sensor}_w30_delta"])
        new[f"derived_sensor_{i}_mean_contrast_15_30"] = (m15 - m30).to_numpy(dtype=float)
        new[f"derived_sensor_{i}_std_ratio_15_30"] = (s15 / (s30.abs() + EPS)).to_numpy(dtype=float)
        new[f"derived_sensor_{i}_delta_contrast_15_30"] = (d15 - d30).to_numpy(dtype=float)
        new[f"derived_sensor_{i}_current_zscore_w30"] = ((context[sensor] - m30) / (s30 + EPS)).to_numpy(dtype=float)
    result = pd.DataFrame(new)
    if not np.isfinite(result.to_numpy(dtype=float)).all():
        raise ValueError("Cross-window derived features contain NaN or infinite values")
    return result


def enhanced_context(frame: pd.DataFrame, add_cross_window: bool = True) -> pd.DataFrame:
    """Return multi-resolution context and optionally the 84 engineered contrasts."""
    base = multiresolution_context(frame)
    if not add_cross_window:
        return base
    derived = cross_window_features(base)
    combined = pd.concat([base, derived], axis=1)
    if not np.isfinite(combined.to_numpy(dtype=float)).all():
        raise ValueError("Enhanced context contains NaN or infinite values")
    return combined


def meta_features(
    context: pd.DataFrame,
    expert_predictions: pd.DataFrame,
    include_disagreement: bool = True,
) -> pd.DataFrame:
    """Combine sensor context and out-of-fold expert predictions for an error gate."""
    forbidden = {"engine_id", "cycle", "RUL", "RUL_true_capped"}
    if forbidden.intersection(context.columns):
        raise ValueError("Gate context must not contain IDs, cycle or RUL target")
    missing = [e for e in EXPERTS if e not in expert_predictions.columns]
    if missing:
        raise ValueError(f"Missing expert predictions: {missing}")
    if len(context) != len(expert_predictions):
        raise ValueError("Context and expert predictions must have equal row counts")
    ctx = context.reset_index(drop=True).astype(np.float32)
    pred = expert_predictions.loc[:, list(EXPERTS)].reset_index(drop=True).astype(float)
    values = pred.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Expert predictions contain non-finite values")
    extra = pred.copy()
    extra.columns = [f"pred_{e}" for e in EXPERTS]
    if include_disagreement:
        mean = values.mean(axis=1)
        extra["expert_mean"] = mean
        extra["expert_spread"] = values.std(axis=1)
        extra["expert_range"] = values.max(axis=1) - values.min(axis=1)
        for i, expert in enumerate(EXPERTS):
            extra[f"abs_deviation_{expert}"] = np.abs(values[:, i] - mean)
    X = pd.concat([ctx, extra], axis=1)
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Gate meta-features contain NaN or infinite values")
    return X


def perturb_sensor_context(
    base_context: pd.DataFrame,
    scale_reference: pd.DataFrame,
    noise_fraction: float,
    seed: int,
) -> pd.DataFrame:
    """Perturb sensor-derived feature columns by a fraction of OOF feature SD.

    This is a feature-input stress test, not a physically simulated sensor failure.
    Settings are left unchanged. Derived cross-window features should be recomputed
    after this function is called.
    """
    if noise_fraction < 0:
        raise ValueError("noise_fraction cannot be negative")
    out = base_context.copy().reset_index(drop=True)
    if noise_fraction == 0:
        return out
    rng = np.random.default_rng(seed)
    sensor_cols = [c for c in out.columns if c.startswith("sensor_")]
    for col in sensor_cols:
        scale = float(pd.to_numeric(scale_reference[col], errors="raise").std(ddof=0))
        if not np.isfinite(scale):
            raise ValueError(f"Non-finite reference scale for {col}")
        if scale > 0:
            out[col] = out[col].to_numpy(dtype=float) + rng.normal(0.0, noise_fraction * scale, size=len(out))
    if not np.isfinite(out.to_numpy(dtype=float)).all():
        raise ValueError("Perturbed context contains NaN or infinite values")
    return out


def permutable_feature_groups(meta: pd.DataFrame) -> dict[str, list[str]]:
    """Return mutually exclusive groups for group-permutation explainability."""
    groups: dict[str, list[str]] = {
        "current_sensors_and_settings": [],
        "window_15_features": [],
        "window_30_features": [],
        "cross_window_engineered": [],
        "expert_predictions": [],
        "expert_disagreement": [],
    }
    for col in meta.columns:
        if col.startswith("pred_"):
            groups["expert_predictions"].append(col)
        elif col == "expert_mean" or col in {"expert_spread", "expert_range"} or col.startswith("abs_deviation_"):
            groups["expert_disagreement"].append(col)
        elif col.startswith("derived_"):
            groups["cross_window_engineered"].append(col)
        elif "_w15_" in col:
            groups["window_15_features"].append(col)
        elif "_w30_" in col:
            groups["window_30_features"].append(col)
        else:
            groups["current_sensors_and_settings"].append(col)
    return {k: v for k, v in groups.items() if v}


def gate_expected_errors(gates: Mapping[str, object], X: pd.DataFrame) -> pd.DataFrame:
    """Predict each expert's expected absolute error in stable expert order."""
    values: dict[str, np.ndarray] = {}
    matrix = X.to_numpy(dtype=np.float32, copy=True)
    for expert in EXPERTS:
        if expert not in gates:
            raise ValueError(f"Missing fitted error gate for {expert}")
        predicted = np.maximum(np.asarray(gates[expert].predict(matrix), dtype=float), 0.0)
        if len(predicted) != len(X) or not np.isfinite(predicted).all():
            raise ValueError(f"Invalid expected-error predictions from gate {expert}")
        values[expert] = predicted
    return pd.DataFrame(values)


def blend_with_gates(
    gates: Mapping[str, object],
    context: pd.DataFrame,
    expert_predictions: pd.DataFrame,
    include_disagreement: bool = True,
    error_floor: float = 0.5,
) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    """Convenience wrapper returning blend, weights and gate feature matrix."""
    X = meta_features(context, expert_predictions, include_disagreement=include_disagreement)
    expected_errors = gate_expected_errors(gates, X)
    blended, weights = adaptive_blend(expert_predictions, expected_errors, error_floor=error_floor)
    return blended, weights, X
