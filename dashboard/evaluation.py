"""Helpers for presenting the latest nested validation comparison."""
from __future__ import annotations
import pandas as pd

V1_METHOD = "V1_adaptive_error_gate"
V2_NESTED_METHOD = "V2_nested_selected"
V2_LEGACY_METHOD = "V2_bounded_shrunk"


def build_v1_v2_comparison(
    metrics: pd.DataFrame,
    selected_subsets: list[str] | tuple[str, ...],
    v2_method: str = V2_NESTED_METHOD,
) -> pd.DataFrame:
    """Build a per-subset comparison from the requested V1 and V2 metric rows."""
    required = {"subset", "method", "rmse", "mae"}
    if not required.issubset(metrics.columns):
        return pd.DataFrame()
    frame = metrics.loc[
        metrics["subset"].isin(list(selected_subsets))
        & metrics["method"].isin([V1_METHOD, v2_method])
    ].copy()
    if frame.empty:
        return pd.DataFrame()
    if frame.duplicated(["subset", "method"]).any():
        raise ValueError("Duplicate V1/V2 metric rows found for a subset")
    wide = frame.pivot(index="subset", columns="method", values=["rmse", "mae"])
    expected = [(metric, method) for metric in ("rmse", "mae") for method in (V1_METHOD, v2_method)]
    if any(column not in wide.columns for column in expected):
        return pd.DataFrame()
    result = pd.DataFrame(index=wide.index)
    result["V1 RMSE"] = pd.to_numeric(wide[("rmse", V1_METHOD)], errors="coerce")
    result["V2 RMSE"] = pd.to_numeric(wide[("rmse", v2_method)], errors="coerce")
    result["V2 − V1 RMSE"] = result["V2 RMSE"] - result["V1 RMSE"]
    result["V1 MAE"] = pd.to_numeric(wide[("mae", V1_METHOD)], errors="coerce")
    result["V2 MAE"] = pd.to_numeric(wide[("mae", v2_method)], errors="coerce")
    result["V2 − V1 MAE"] = result["V2 MAE"] - result["V1 MAE"]
    result["Lower RMSE in this run"] = result["V2 − V1 RMSE"].map(
        lambda delta: "V2" if delta < -1e-10 else ("Tie" if abs(delta) <= 1e-10 else "V1")
    )
    result.index.name = "Subset"
    return result.reset_index()
