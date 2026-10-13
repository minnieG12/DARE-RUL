"""Core utilities for leakage-aware Phase 5 C-MAPSS baseline experiments."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit

SENSOR_COLUMNS = [f"sensor_{i}" for i in range(1, 22)]
SETTING_COLUMNS = ["setting_1", "setting_2", "setting_3"]


def select_feature_columns(frame: pd.DataFrame, window: int) -> list[str]:
    """Select settings, current sensors and only the chosen window's temporal features.

    engine_id and cycle are identifiers/ordering keys, not model inputs. RUL is the
    target and is never included in X.
    """
    if window not in (15, 30):
        raise ValueError("window must be 15 or 30")
    required = SETTING_COLUMNS + SENSOR_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Feature table is missing required columns: {missing[:5]}")
    window_columns = [
        column for column in frame.columns
        if column.startswith("sensor_") and f"_w{window}_" in column
    ]
    # Keep ordering stable so saved feature lists and models are reproducible.
    columns = required + sorted(window_columns)
    if "RUL" in columns or "engine_id" in columns or "cycle" in columns:
        raise AssertionError("Target/identifier accidentally selected as model features")
    return columns


def capped_target(frame: pd.DataFrame, rul_cap: int | None) -> np.ndarray:
    """Create target vector; a cap of None leaves labels uncapped."""
    if "RUL" not in frame.columns:
        raise ValueError("Feature table does not contain the RUL target")
    y = pd.to_numeric(frame["RUL"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("RUL target must contain finite, non-negative values")
    if rul_cap is not None:
        if rul_cap < 1:
            raise ValueError("rul_cap must be positive or None")
        y = np.minimum(y, rul_cap)
    return y


def split_by_engine(
    frame: pd.DataFrame, validation_fraction: float = 0.2, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Split row indices while keeping every engine wholly in one split."""
    if "engine_id" not in frame.columns:
        raise ValueError("engine_id is required for engine-separated validation")
    if not 0.05 <= validation_fraction <= 0.5:
        raise ValueError("validation_fraction must be between 0.05 and 0.5")
    groups = frame["engine_id"].to_numpy()
    if len(np.unique(groups)) < 5:
        raise ValueError("At least five engines are required for a stable split")
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=validation_fraction, random_state=seed
    )
    train_idx, validation_idx = next(splitter.split(frame, groups=groups))
    train_engines = set(groups[train_idx].tolist())
    validation_engines = set(groups[validation_idx].tolist())
    if train_engines & validation_engines:
        raise AssertionError("Engine leakage detected between train and validation")
    return train_idx, validation_idx


def build_regressor(model_kind: str, seed: int = 42):
    """Build fixed, documented classical ML baselines; no validation tuning."""
    if model_kind == "RF":
        return RandomForestRegressor(
            n_estimators=120,
            max_features=0.7,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        )
    if model_kind == "HGB":
        return HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.08,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=seed,
            early_stopping=False,
        )
    raise ValueError("model_kind must be 'RF' or 'HGB'")


def clipped_predictions(predictions: Iterable[float], rul_cap: int | None) -> np.ndarray:
    values = np.asarray(list(predictions), dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Model predictions contain non-finite values")
    upper = float(rul_cap) if rul_cap is not None else np.inf
    return np.clip(values, 0.0, upper)


def calculate_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    """Return RMSE, MAE and PHM08/NASA asymmetric score for aligned arrays.

    Error is prediction - truth. Over-predicting RUL receives denominator 10;
    under-predicting RUL receives denominator 13. Lower is better for all metrics.
    """
    true = np.asarray(list(y_true), dtype=float)
    pred = np.asarray(list(y_pred), dtype=float)
    if true.size == 0 or pred.size == 0 or true.shape != pred.shape:
        raise ValueError("y_true and y_pred must be non-empty arrays of equal shape")
    if not np.isfinite(true).all() or not np.isfinite(pred).all():
        raise ValueError("Metric inputs must be finite")
    error = pred - true
    rmse = float(np.sqrt(np.mean(np.square(error))))
    mae = float(np.mean(np.abs(error)))
    per_row_score = np.where(error < 0, np.expm1(-error / 13.0), np.expm1(error / 10.0))
    return {
        "rmse": rmse,
        "mae": mae,
        "nasa_score_sum": float(np.sum(per_row_score)),
        "nasa_score_mean": float(np.mean(per_row_score)),
    }
