"""Exploratory validation-only comparison of the bounded V2 combiner.

Uses existing Phase 6 held-out validation predictions and expected-error
artifacts. It does NOT read Phase 8 official test labels or modify models. Since
this validation cohort has already been used for prior comparisons, results are
exploratory for V2 development, not an untouched final comparison.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase5.baseline_core import calculate_metrics  # noqa: E402
from scripts.phase6.ensemble_core import EXPERTS, engine_macro_metrics  # noqa: E402
from scripts.phase9.ensemble_v2 import blend_v2  # noqa: E402

SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase6-results-dir", type=Path, default=ROOT / "results" / "phase6")
    p.add_argument("--output-dir", type=Path, default=ROOT / "results" / "phase9")
    p.add_argument("--subsets", nargs="+", choices=SUBSETS, default=list(SUBSETS))
    p.add_argument("--rul-cap", type=float, default=125.0)
    p.add_argument("--error-floor", type=float, default=0.5)
    p.add_argument("--max-weight", type=float, default=0.65)
    p.add_argument("--shrinkage", type=float, default=0.20)
    p.add_argument("--bootstrap-reps", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def _load_static_weights(path: Path, subset: str) -> dict[str, float]:
    table = pd.read_csv(path)
    required = {"subset", "expert", "static_weight"}
    if not required.issubset(table.columns):
        raise ValueError(f"{path} needs columns {sorted(required)}")
    rows = table.loc[table.subset == subset]
    if set(rows.expert) != set(EXPERTS) or rows.expert.duplicated().any():
        raise ValueError(f"{subset}: static OOF reliability must have exactly one row per expert")
    return {str(r.expert): float(r.static_weight) for r in rows.itertuples(index=False)}


def _bootstrap_rmse_difference(
    frame: pd.DataFrame, y_col: str, old_col: str, new_col: str,
    reps: int, seed: int,
) -> dict[str, float]:
    """Paired engine-block bootstrap of RMSE(V2)-RMSE(V1); negative favors V2."""
    engines = np.asarray(sorted(frame.engine_id.astype(int).unique()), dtype=int)
    if len(engines) < 2 or reps < 1:
        return {"median_diff": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    groups = {int(e): frame.loc[frame.engine_id.astype(int) == int(e)] for e in engines}
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(reps):
        sampled = rng.choice(engines, size=len(engines), replace=True)
        pieces = [groups[int(e)] for e in sampled]
        boot = pd.concat(pieces, ignore_index=True)
        y = boot[y_col].to_numpy(float)
        old = boot[old_col].to_numpy(float)
        new = boot[new_col].to_numpy(float)
        diffs.append(float(np.sqrt(np.mean((new - y) ** 2)) - np.sqrt(np.mean((old - y) ** 2))))
    return {
        "median_diff": float(np.median(diffs)),
        "ci_low": float(np.quantile(diffs, 0.025)),
        "ci_high": float(np.quantile(diffs, 0.975)),
    }


def run_subset(subset: str, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    pred_path = args.phase6_results_dir / "validation_predictions.csv"
    reliability_path = args.phase6_results_dir / "oof_reliability.csv"
    error_path = args.phase6_results_dir / subset / "adaptive_expected_errors_validation.csv"
    for path in (pred_path, reliability_path, error_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing Phase 6 validation artifact: {path}. Complete Phase 6 first.")

    predictions = pd.read_csv(pred_path)
    required = {"subset", "method", "engine_id", "cycle", "RUL_true_capped", "RUL_pred"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"{pred_path.name} missing columns: {sorted(required - set(predictions.columns))}")
    frame = predictions.loc[predictions.subset == subset].copy()
    if frame.empty:
        raise ValueError(f"No Phase 6 validation prediction rows for {subset}")
    keys = ["engine_id", "cycle", "RUL_true_capped"]
    expert_rows = frame.loc[frame.method.isin(EXPERTS)]
    wide = expert_rows.pivot(index=keys, columns="method", values="RUL_pred").reset_index()
    wide.columns.name = None
    if set(EXPERTS) - set(wide.columns):
        raise ValueError(f"{subset}: not all four expert validation predictions are present")
    if wide.duplicated(["engine_id", "cycle"]).any() or wide[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: expert validation rows are duplicated or incomplete")

    v1 = frame.loc[frame.method == "adaptive_error_gate", keys + ["RUL_pred"]].rename(columns={"RUL_pred": "pred_V1"})
    if v1.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: V1 validation rows are duplicated")
    error_frame = pd.read_csv(error_path)
    error_cols = [f"expected_error_{expert}" for expert in EXPERTS]
    if not {"subset", "engine_id", "cycle", *error_cols}.issubset(error_frame.columns):
        raise ValueError(f"{error_path.name} is missing required expected-error columns")
    error_frame = error_frame.rename(columns={f"expected_error_{e}": f"err_{e}" for e in EXPERTS})
    if error_frame.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: expected-error validation rows contain duplicate keys")

    joined = wide.merge(v1, on=keys, how="inner", validate="one_to_one")
    joined = joined.merge(
        error_frame[["engine_id", "cycle", *[f"err_{e}" for e in EXPERTS]]],
        on=["engine_id", "cycle"], how="left", validate="one_to_one",
    )
    if len(joined) != len(wide) or joined[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: key alignment failed between expert, V1, and error prediction data")
    expected_error = joined[[f"err_{e}" for e in EXPERTS]].copy()
    expected_error.columns = list(EXPERTS)
    expert_prediction = joined[list(EXPERTS)].copy()
    static = _load_static_weights(reliability_path, subset)
    v2_pred, weights, fallback = blend_v2(
        expert_prediction[list(EXPERTS)], expected_error, static,
        rul_cap=args.rul_cap, error_floor=args.error_floor,
        max_weight=args.max_weight, shrinkage=args.shrinkage,
    )
    joined["pred_V2"] = v2_pred
    joined["v2_fallback_reason"] = fallback
    for idx, name in enumerate(EXPERTS):
        joined[f"v2_weight_{name}"] = weights.iloc[:, idx].to_numpy()
    y = joined["RUL_true_capped"].to_numpy(dtype=float)
    engine_ids = joined["engine_id"].to_numpy(dtype=int)
    method_predictions = {name: joined[name].to_numpy(dtype=float) for name in EXPERTS}
    method_predictions["equal_average"] = joined[list(EXPERTS)].mean(axis=1).to_numpy(dtype=float)
    method_predictions["V1_adaptive_error_gate"] = joined["pred_V1"].to_numpy(dtype=float)
    method_predictions["V2_bounded_shrunk"] = joined["pred_V2"].to_numpy(dtype=float)
    static_vec = np.asarray([static[name] for name in EXPERTS], dtype=float)
    static_vec /= static_vec.sum()
    method_predictions["static_OOF_inverse_MAE"] = expert_prediction.to_numpy(dtype=float) @ static_vec

    metric_rows = []
    for method, pred in method_predictions.items():
        row_metrics = calculate_metrics(y, pred)
        macro = engine_macro_metrics(engine_ids, y, pred)
        metric_rows.append({"subset": subset, "method": method, "rows": len(joined), "engines": int(pd.Series(engine_ids).nunique()), **row_metrics, **macro})
    paired = joined[["engine_id", "RUL_true_capped", "pred_V1", "pred_V2"]]
    bootstrap = _bootstrap_rmse_difference(paired, "RUL_true_capped", "pred_V1", "pred_V2", args.bootstrap_reps, args.seed)
    info = {
        "subset": subset, "status": "EXPLORATORY_VALIDATION_ONLY",
        "v1_rmse": float(np.sqrt(np.mean((y - joined.pred_V1.to_numpy(float)) ** 2))),
        "v2_rmse": float(np.sqrt(np.mean((y - joined.pred_V2.to_numpy(float)) ** 2))),
        "rmse_diff_v2_minus_v1_bootstrap": bootstrap,
        "fallback_rows": int((joined.v2_fallback_reason != "").sum()),
        "parameters": {"rul_cap": args.rul_cap, "error_floor": args.error_floor, "max_weight": args.max_weight, "shrinkage": args.shrinkage, "bootstrap_reps": args.bootstrap_reps, "seed": args.seed},
        "limitations": [
            "This reuses the Phase 6 held-out validation cohort previously used for comparisons; V2 results are exploratory, not an untouched final selection estimate.",
            "No Phase 8 official test targets are loaded by this script.",
            "Do not select/tune V2 parameters using Phase 8 official test results.",
        ],
    }
    return pd.DataFrame(metric_rows), joined, info


def main() -> int:
    args = parse_args()
    if args.rul_cap <= 0 or args.bootstrap_reps < 1:
        raise SystemExit("rul-cap and bootstrap-reps must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_metrics, all_predictions, metadata = [], [], {"phase": 9, "status": "EXPLORATORY_VALIDATION_ONLY", "subsets": []}
    for subset in args.subsets:
        print(f"Evaluating V2 on existing Phase 6 validation data: {subset}", flush=True)
        metrics, predictions, info = run_subset(subset, args)
        all_metrics.append(metrics)
        all_predictions.append(predictions.assign(subset=subset))
        metadata["subsets"].append(info)
        print(f"  V1 RMSE={info['v1_rmse']:.4f}; V2 RMSE={info['v2_rmse']:.4f}; bootstrap difference={info['rmse_diff_v2_minus_v1_bootstrap']}", flush=True)
    metric_frame = pd.concat(all_metrics, ignore_index=True)
    prediction_frame = pd.concat(all_predictions, ignore_index=True)
    metric_frame.to_csv(args.output_dir / "ensemble_v2_validation_metrics.csv", index=False)
    prediction_frame.to_csv(args.output_dir / "ensemble_v2_validation_predictions.csv", index=False)
    (args.output_dir / "ensemble_v2_validation_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("PHASE 9 V2 VALIDATION PASS (EXPLORATORY; NO OFFICIAL TEST LABELS READ)")
    print(f"Metrics: {args.output_dir / 'ensemble_v2_validation_metrics.csv'}")
    print(f"Predictions: {args.output_dir / 'ensemble_v2_validation_predictions.csv'}")
    print(f"Metadata: {args.output_dir / 'ensemble_v2_validation_metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
