"""Helpers for leakage-aware DARE-RUL Phase 6 ensemble experiments."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

EXPERTS = ("RF15", "HGB15", "RF30", "HGB30")
PREDICTION_COLUMNS = {name: f"pred_{name}" for name in EXPERTS}


def inverse_error_weights(error_by_expert: dict[str, float], floor: float = 0.5) -> dict[str, float]:
    """Convert positive estimated errors into normalized inverse-error weights.

    Lower expected error gives a larger weight. A floor prevents a near-zero
    error estimate from taking effectively all the weight.
    """
    if floor <= 0:
        raise ValueError("floor must be positive")
    if any(name not in EXPERTS for name in error_by_expert):
        raise ValueError("Unknown expert supplied")
    if set(error_by_expert) != set(EXPERTS):
        raise ValueError(f"Expected error estimates for exactly: {EXPERTS}")
    values = np.asarray([error_by_expert[name] for name in EXPERTS], dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Error estimates must be finite and non-negative")
    inverse = 1.0 / (values + floor)
    inverse /= inverse.sum()
    return {name: float(inverse[i]) for i, name in enumerate(EXPERTS)}


def static_inverse_mae_weights(mae_by_expert: dict[str, float], floor: float = 0.5) -> dict[str, float]:
    """Build static blending weights from training-only out-of-fold engine-macro MAE."""
    return inverse_error_weights(mae_by_expert, floor=floor)


def make_gate_features(context: pd.DataFrame, expert_predictions: pd.DataFrame) -> pd.DataFrame:
    """Combine temporal context with expert predictions and disagreement features.

    `context` must already exclude `engine_id`, `cycle`, and `RUL`. Predictions
    must have one column for each EXPERT. Disagreement is represented by the
    expert mean, spread, range and each expert's deviation from the mean.
    """
    if any(column in context.columns for column in ("engine_id", "cycle", "RUL")):
        raise ValueError("Gate context must exclude engine_id, cycle and RUL")
    missing = [name for name in EXPERTS if name not in expert_predictions.columns]
    if missing:
        raise ValueError(f"Missing expert prediction columns: {missing}")
    if len(context) != len(expert_predictions):
        raise ValueError("Context and expert predictions must have equal row counts")
    context_array = context.reset_index(drop=True).astype(np.float32)
    predictions = expert_predictions.loc[:, list(EXPERTS)].reset_index(drop=True).astype(float)
    values = predictions.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Expert predictions contain NaN or infinite values")
    mean = values.mean(axis=1)
    spread = values.std(axis=1)
    low = values.min(axis=1)
    high = values.max(axis=1)
    extras = predictions.copy()
    extras.columns = [PREDICTION_COLUMNS[name] for name in EXPERTS]
    extras["expert_mean"] = mean
    extras["expert_spread"] = spread
    extras["expert_range"] = high - low
    for i, name in enumerate(EXPERTS):
        extras[f"abs_deviation_{name}"] = np.abs(values[:, i] - mean)
    combined = pd.concat([context_array, extras], axis=1)
    if not np.isfinite(combined.to_numpy(dtype=float)).all():
        raise ValueError("Gate features contain NaN or infinite values")
    return combined



def build_validation_error_artifact(
    subset: str, validation_keys: pd.DataFrame, expected_errors: pd.DataFrame
) -> pd.DataFrame:
    """Create a row-aligned expected-error artifact for held-out validation rows.

    `expected_errors` are predicted by the fitted gates on validation context, so
    their keys must come from the validation rows—not from the OOF training rows.
    """
    missing_keys = {"engine_id", "cycle"} - set(validation_keys.columns)
    missing_errors = set(EXPERTS) - set(expected_errors.columns)
    if missing_keys:
        raise ValueError(f"Validation keys missing columns: {sorted(missing_keys)}")
    if missing_errors:
        raise ValueError(f"Expected-error data missing experts: {sorted(missing_errors)}")
    if len(validation_keys) != len(expected_errors):
        raise ValueError(
            "Validation key rows and expected-error rows must have equal length "
            f"({len(validation_keys)} != {len(expected_errors)})"
        )
    keys = validation_keys.loc[:, ["engine_id", "cycle"]].reset_index(drop=True)
    errors = expected_errors.loc[:, list(EXPERTS)].reset_index(drop=True).astype(float)
    if keys.isna().any().any() or keys.duplicated(["engine_id", "cycle"]).any():
        raise ValueError("Validation keys must be non-null and unique by engine_id/cycle")
    if not np.isfinite(errors.to_numpy(dtype=float)).all():
        raise ValueError("Expected-error predictions must be finite")
    artifact = pd.DataFrame({
        "subset": subset,
        "engine_id": keys["engine_id"].astype(int),
        "cycle": keys["cycle"].astype(int),
    })
    for expert in EXPERTS:
        artifact[f"expected_error_{expert}"] = errors[expert].to_numpy(dtype=float)
    return artifact

def adaptive_blend(
    expert_predictions: pd.DataFrame,
    expected_errors: pd.DataFrame,
    error_floor: float = 0.5,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Blend predictions with per-row inverse estimated-error weights.

    Error predictions are clipped at zero; `error_floor` bounds the maximum
    influence of an expert. Returns blended predictions and per-row weights.
    """
    missing_pred = [name for name in EXPERTS if name not in expert_predictions.columns]
    missing_err = [name for name in EXPERTS if name not in expected_errors.columns]
    if missing_pred or missing_err:
        raise ValueError(f"Missing predictions {missing_pred}; missing errors {missing_err}")
    pred = expert_predictions.loc[:, list(EXPERTS)].to_numpy(dtype=float)
    err = expected_errors.loc[:, list(EXPERTS)].to_numpy(dtype=float)
    if pred.shape != err.shape or pred.shape[0] == 0:
        raise ValueError("Prediction/error matrices must be non-empty and have matching shapes")
    if not np.isfinite(pred).all() or not np.isfinite(err).all():
        raise ValueError("Prediction/error matrices must be finite")
    if error_floor <= 0:
        raise ValueError("error_floor must be positive")
    inverse = 1.0 / (np.maximum(err, 0.0) + error_floor)
    row_sums = inverse.sum(axis=1, keepdims=True)
    weights = inverse / row_sums
    blended = np.sum(pred * weights, axis=1)
    weight_frame = pd.DataFrame(weights, columns=[f"weight_{name}" for name in EXPERTS])
    if not np.isfinite(blended).all() or not np.allclose(weights.sum(axis=1), 1.0):
        raise AssertionError("Adaptive blend produced invalid predictions or weights")
    return blended, weight_frame


def engine_balanced_sample_weights(engine_ids: Iterable[int]) -> np.ndarray:
    """Weights each engine to total weight 1, so longer trajectories do not dominate gate fitting."""
    engines = pd.Series(list(engine_ids))
    if engines.empty or engines.isna().any():
        raise ValueError("engine_ids must be non-empty and non-null")
    counts = engines.map(engines.value_counts()).to_numpy(dtype=float)
    return 1.0 / counts


def build_error_gate(seed: int = 42) -> HistGradientBoostingRegressor:
    """Small, fixed gate model; it is not tuned on the held-out validation engines."""
    return HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.05,
        max_leaf_nodes=15,
        min_samples_leaf=50,
        l2_regularization=2.0,
        random_state=seed,
        early_stopping=False,
    )


def metric_summary(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    """RMSE, MAE and PHM08/NASA score using the same sign convention as Phase 5."""
    true = np.asarray(list(y_true), dtype=float)
    pred = np.asarray(list(y_pred), dtype=float)
    if true.size == 0 or true.shape != pred.shape:
        raise ValueError("Metric arrays must be non-empty and have matching shapes")
    if not np.isfinite(true).all() or not np.isfinite(pred).all():
        raise ValueError("Metric arrays must be finite")
    error = pred - true
    score = np.where(error < 0, np.expm1(-error / 13.0), np.expm1(error / 10.0))
    return {
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "mae": float(np.mean(np.abs(error))),
        "nasa_score_sum": float(score.sum()),
        "nasa_score_mean": float(score.mean()),
    }


def engine_macro_metrics(engine_ids: Iterable[int], y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    """Average each engine's metrics equally to complement row-weighted scores."""
    frame = pd.DataFrame({
        "engine_id": list(engine_ids),
        "y_true": list(y_true),
        "y_pred": list(y_pred),
    })
    if frame.empty or frame.isna().any().any():
        raise ValueError("Engine-macro metric inputs must be non-empty and non-null")
    summaries = []
    for _, group in frame.groupby("engine_id", sort=False):
        summaries.append(metric_summary(group.y_true, group.y_pred))
    return {
        "engine_macro_rmse": float(np.mean([m["rmse"] for m in summaries])),
        "engine_macro_mae": float(np.mean([m["mae"] for m in summaries])),
        "engine_macro_nasa_score_mean": float(np.mean([m["nasa_score_mean"] for m in summaries])),
    }
