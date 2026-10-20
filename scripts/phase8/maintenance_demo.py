"""Create an illustrative maintenance-priority CSV from prediction-only Phase 8 output.

This demo uses predicted RUL only. It never reads official RUL targets or scored files.
Risk thresholds are illustrative user-configurable values, not approved aircraft policy.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def recommendation_for_rul(predicted_rul: float, critical_threshold: float = 10.0, high_threshold: float = 30.0) -> tuple[str, str]:
    """Return illustrative status and follow-up text from predicted RUL."""
    if not np.isfinite(float(predicted_rul)) or float(predicted_rul) < 0:
        raise ValueError("predicted_rul must be finite and non-negative")
    if critical_threshold < 0 or high_threshold <= critical_threshold:
        raise ValueError("thresholds must satisfy 0 <= critical < high")
    value = float(predicted_rul)
    if value <= critical_threshold:
        return "CRITICAL", "Prioritize inspection and maintenance assessment"
    if value <= high_threshold:
        return "HIGH", "Schedule a planned inspection soon"
    return "MONITOR", "Continue monitoring and refresh the estimate with new telemetry"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=ROOT / "results" / "phase8" / "test_predictions.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "phase8" / "maintenance_recommendations.csv")
    parser.add_argument("--critical-threshold", type=float, default=10.0)
    parser.add_argument("--high-threshold", type=float, default=30.0)
    args = parser.parse_args()

    if args.high_threshold <= args.critical_threshold or args.critical_threshold < 0:
        raise SystemExit("ERROR: thresholds must satisfy 0 <= critical < high")
    if not args.predictions.exists():
        raise SystemExit(f"ERROR: {args.predictions} not found. Run Phase 8 evaluation first.")
    frame = pd.read_csv(args.predictions)
    required = {"subset", "engine_id", "final_cycle", "selected_method", "predicted_rul"}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(f"ERROR: predictions file missing columns: {sorted(missing)}")
    if frame.empty or frame.predicted_rul.isna().any():
        raise SystemExit("ERROR: predictions file is empty or has missing RUL predictions")
    # Explicitly guard against accidentally using the scored file as this demo input.
    if "RUL_true" in frame.columns or "error_pred_minus_true" in frame.columns:
        raise SystemExit("ERROR: use prediction-only test_predictions.csv, never the scored predictions file")

    classified = [recommendation_for_rul(v, args.critical_threshold, args.high_threshold) for v in frame.predicted_rul]
    frame["risk_tier"] = [item[0] for item in classified]
    frame["illustrative_next_step"] = [item[1] for item in classified]
    frame["critical_threshold_cycles"] = args.critical_threshold
    frame["high_threshold_cycles"] = args.high_threshold
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.sort_values(["risk_tier", "predicted_rul"], ascending=[True, True], kind="stable").to_csv(args.output, index=False)

    print("PHASE 8 MAINTENANCE DEMO PASS")
    print(f"Input:  {args.predictions}")
    print(f"Output: {args.output}")
    print(f"Illustrative rules: CRITICAL <= {args.critical_threshold}; HIGH <= {args.high_threshold}; else MONITOR")
    print(frame.groupby(["subset", "risk_tier"]).size().rename("engine_count").to_string())
    print("WARNING: demo tiers are illustrative, not approved aviation maintenance instructions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
