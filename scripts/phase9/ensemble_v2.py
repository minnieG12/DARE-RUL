"""Bounded, shrinkage-stabilized adaptive blending helper for Phase 9 experiments.

This is an experimental combiner utility. It does not train experts/gates and must
be evaluated on engine-separated validation data before it is adopted.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

EXPERTS = ("RF15", "HGB15", "RF30", "HGB30")


def _normalized_static(static_weights: Mapping[str, float]) -> np.ndarray:
    if set(static_weights) != set(EXPERTS):
        raise ValueError(f"static_weights must contain exactly {EXPERTS}")
    values = np.asarray([static_weights[name] for name in EXPERTS], dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        raise ValueError("Static weights must be finite, non-negative, and have positive total")
    return values / values.sum()


def _cap_project(weights: np.ndarray, max_weight: float) -> np.ndarray:
    """Project positive weights onto a capped simplex; sum=1 and each <= max_weight."""
    w = np.asarray(weights, dtype=float).copy()
    n = len(w)
    if not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        w = np.ones(n, dtype=float)
    if max_weight < 1.0 / n or max_weight > 1.0:
        raise ValueError(f"max_weight must be between {1.0/n:.3f} and 1.0 for {n} experts")
    w /= w.sum()
    if np.all(w <= max_weight + 1e-12):
        return w
    out = np.zeros(n, dtype=float)
    active = np.ones(n, dtype=bool)
    remaining = 1.0
    for _ in range(n + 1):
        idx = np.flatnonzero(active)
        if len(idx) == 0 or remaining <= 1e-12:
            break
        candidate = w[idx]
        if candidate.sum() <= 0:
            candidate = np.ones(len(idx), dtype=float)
        proposal = candidate / candidate.sum() * remaining
        too_large = proposal > max_weight + 1e-12
        if not too_large.any():
            out[idx] = proposal
            remaining = 0.0
            break
        capped_idx = idx[too_large]
        out[capped_idx] = max_weight
        active[capped_idx] = False
        remaining = max(0.0, 1.0 - out.sum())
    if remaining > 1e-8:
        idx = np.flatnonzero(active)
        if not len(idx):
            raise ValueError("Cannot allocate weight mass under max_weight")
        out[idx] += remaining / len(idx)
    out = np.maximum(out, 0.0)
    out /= out.sum()
    if (out > max_weight + 1e-8).any() or not np.isclose(out.sum(), 1.0):
        raise AssertionError("Capped-simplex projection failed")
    return out


def blend_v2(
    expert_predictions: pd.DataFrame,
    expected_errors: pd.DataFrame,
    static_weights: Mapping[str, float],
    *,
    rul_cap: float = 125.0,
    error_floor: float = 0.5,
    max_weight: float = 0.65,
    shrinkage: float = 0.20,
) -> tuple[np.ndarray, pd.DataFrame, pd.Series]:
    """Blend finite expert predictions with bounded adaptive weights.

    Invalid expected-error rows fall back to normalized static weights. Invalid
    expert predictions raise, because silently hiding a broken expert is unsafe.
    `shrinkage` mixes each adaptive weight vector with static weights before the
    maximum-weight cap. Returns predictions, weights, and fallback reason per row.
    """
    missing_p = set(EXPERTS) - set(expert_predictions.columns)
    missing_e = set(EXPERTS) - set(expected_errors.columns)
    if missing_p or missing_e:
        raise ValueError(f"Missing prediction experts {sorted(missing_p)}; missing error experts {sorted(missing_e)}")
    pred = expert_predictions.loc[:, list(EXPERTS)].to_numpy(dtype=float)
    err = expected_errors.loc[:, list(EXPERTS)].to_numpy(dtype=float)
    if pred.ndim != 2 or pred.shape != err.shape or pred.shape[0] == 0:
        raise ValueError("Prediction and error matrices must be non-empty and have identical shapes")
    if not np.isfinite(pred).all():
        raise ValueError("Expert predictions must be finite; cannot safely blend a broken expert")
    if rul_cap <= 0 or error_floor <= 0:
        raise ValueError("rul_cap and error_floor must be positive")
    if not 0.0 <= shrinkage <= 1.0:
        raise ValueError("shrinkage must be between 0 and 1")
    if max_weight < 0.25 or max_weight > 1.0:
        raise ValueError("max_weight must be between 0.25 and 1.0 for four experts")

    static = _cap_project(_normalized_static(static_weights), max_weight)
    out_w = np.zeros_like(pred, dtype=float)
    fallback_reasons: list[str] = []
    for row_idx, row in enumerate(err):
        if not np.isfinite(row).all():
            out_w[row_idx] = static
            fallback_reasons.append("non_finite_expected_error")
            continue
        nonnegative_error = np.maximum(row, 0.0)
        inverse = 1.0 / (nonnegative_error + error_floor)
        adaptive = inverse / inverse.sum()
        stabilized = (1.0 - shrinkage) * adaptive + shrinkage * static
        out_w[row_idx] = _cap_project(stabilized, max_weight)
        fallback_reasons.append("")

    prediction = np.sum(pred * out_w, axis=1)
    prediction = np.clip(prediction, 0.0, float(rul_cap))
    if not np.isfinite(prediction).all() or not np.isfinite(out_w).all():
        raise AssertionError("V2 produced non-finite output")
    if not np.allclose(out_w.sum(axis=1), 1.0, atol=1e-8):
        raise AssertionError("V2 weights must sum to one")
    weights = pd.DataFrame(out_w, columns=[f"weight_{name}" for name in EXPERTS])
    fallbacks = pd.Series(fallback_reasons, name="fallback_reason")
    return prediction, weights, fallbacks
