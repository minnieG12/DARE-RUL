"""Safe loaders and schema checks for the saved Phase 8 experiment artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
EXPERTS = ("RF15", "HGB15", "RF30", "HGB30")
KEYS = ["subset", "engine_id"]
PREDICTION_REQUIRED = {
    "subset", "engine_id", "final_cycle", "selected_method", "training_rul_cap", "predicted_rul",
    *[f"pred_{x}" for x in EXPERTS],
    *[f"expected_error_{x}" for x in EXPERTS],
    *[f"weight_{x}" for x in EXPERTS],
}
SCORED_REQUIRED = PREDICTION_REQUIRED | {"RUL_true", "error_pred_minus_true", "absolute_error"}
METRIC_REQUIRED = {"subset", "selected_method", "test_engines", "rmse", "mae", "nasa_score_sum", "nasa_score_mean"}
MAINT_REQUIRED = PREDICTION_REQUIRED | {"risk_tier", "illustrative_next_step"}


@dataclass
class Phase8Artifacts:
    predictions: pd.DataFrame
    scored: pd.DataFrame
    metrics: pd.DataFrame
    maintenance: pd.DataFrame
    root: Path


def _read_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required project artifact not found: {path}")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")
    return frame


def load_phase8_artifacts(root: str | Path) -> Phase8Artifacts:
    """Load saved outputs only; never reruns the official evaluation."""
    root = Path(root).resolve()
    folder = root / "results" / "phase8"
    predictions = _read_csv(folder / "test_predictions.csv", PREDICTION_REQUIRED)
    scored = _read_csv(folder / "test_scored_predictions.csv", SCORED_REQUIRED)
    metrics = _read_csv(folder / "final_test_metrics.csv", METRIC_REQUIRED)
    maintenance = _read_csv(folder / "maintenance_recommendations.csv", MAINT_REQUIRED)

    for label, frame in (("predictions", predictions), ("scored", scored), ("maintenance", maintenance)):
        if frame.duplicated(KEYS).any():
            raise ValueError(f"{label} contains duplicate subset/engine keys")
        if not set(frame["subset"].astype(str)).issubset(SUBSETS):
            raise ValueError(f"{label} contains unexpected subset names")

    prediction_keys = predictions[KEYS].astype({"subset": str, "engine_id": int}).sort_values(KEYS).reset_index(drop=True)
    scored_keys = scored[KEYS].astype({"subset": str, "engine_id": int}).sort_values(KEYS).reset_index(drop=True)
    maintenance_keys = maintenance[KEYS].astype({"subset": str, "engine_id": int}).sort_values(KEYS).reset_index(drop=True)
    if not prediction_keys.equals(scored_keys):
        raise ValueError("Prediction and scored artifact engine keys do not match")
    if not prediction_keys.equals(maintenance_keys):
        raise ValueError("Prediction and maintenance artifact engine keys do not match")

    if set(metrics["subset"].astype(str)) != set(SUBSETS):
        raise ValueError("final_test_metrics.csv must contain exactly FD001–FD004")
    return Phase8Artifacts(predictions, scored, metrics, maintenance, root)


def filtered_fleet(artifacts: Phase8Artifacts, subsets: list[str], risk_tiers: list[str], query: str = "") -> pd.DataFrame:
    frame = artifacts.predictions.merge(
        artifacts.maintenance[KEYS + ["risk_tier", "illustrative_next_step"]],
        on=KEYS, how="left", validate="one_to_one", suffixes=("", "_maintenance"),
    )
    frame = frame.loc[frame["subset"].isin(subsets)].copy()
    if risk_tiers:
        frame = frame.loc[frame["risk_tier"].isin(risk_tiers)]
    if query.strip():
        q = query.strip()
        frame = frame.loc[
            frame["engine_id"].astype(str).str.contains(q, case=False)
            | frame["subset"].astype(str).str.contains(q, case=False)
        ]
    return frame.sort_values(["subset", "predicted_rul", "engine_id"], kind="stable").reset_index(drop=True)
