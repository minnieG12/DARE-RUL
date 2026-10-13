"""Run engine-separated validation baselines on Phase 4 C-MAPSS features."""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase5.baseline_core import (  # noqa: E402
    build_regressor,
    calculate_metrics,
    capped_target,
    clipped_predictions,
    select_feature_columns,
    split_by_engine,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "features" / "phase4")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results" / "phase5")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "models" / "phase5")
    parser.add_argument("--subsets", nargs="+", choices=["FD001", "FD002", "FD003", "FD004"], default=["FD001", "FD002", "FD003", "FD004"])
    parser.add_argument("--rul-cap", type=int, default=125, help="Use 125 for primary benchmark; use 0 to disable cap")
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trees", type=int, default=120, help="Random Forest tree count")
    parser.add_argument("--max-iter", type=int, default=150, help="HistGradientBoosting iteration count")
    return parser.parse_args()


def validate_inputs(data_dir: Path, subsets: list[str]) -> None:
    for subset in subsets:
        folder = data_dir / subset
        required = [folder / "train_features.parquet"]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(
                "Required Phase 4 feature files are missing: " + ", ".join(missing)
                + ". Run scripts/phase4/run_phase4.ps1 first."
            )


def write_summary(
    metrics: pd.DataFrame,
    out_path: Path,
    cap: int | None,
    seed: int,
    val_fraction: float,
    feature_counts: dict[str, int],
) -> None:
    lines = [
        "# Phase 5 Run Summary — Classical ML Baselines",
        "",
        "- **Status:** PASS (baseline training and engine-separated validation completed)",
        f"- **RUL cap used for this run:** {'uncapped' if cap is None else cap}",
        f"- **Engine-separated validation fraction:** {val_fraction:.0%}",
        f"- **Random seed:** {seed}",
        "- **Validation features:** operating settings, current sensor values and one selected temporal window; `engine_id` and `cycle` excluded.",
        "- **Official test RUL labels:** not read or used in this phase.",
        "- **Target cap note:** 125 is a common C-MAPSS benchmark convention; this run uses it as a provisional primary configuration. Complete close-paper review and protocol approval before publication claims.",
        "",
        "## Validation results",
        "",
        "Lower is better for RMSE, MAE and NASA score. Scores here are calculated across all cycle rows belonging to the held-out validation engines; longer trajectories therefore contribute more rows.",
        "",
        "| Subset | Model | Window | Train engines | Validation engines | Validation rows | Features | RMSE | MAE | NASA score (sum) | NASA score (mean) | Fit seconds |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in metrics.sort_values(["subset", "rmse"]).itertuples(index=False):
        lines.append(
            f"| {r.subset} | {r.model} | {r.window} | {r.train_engines} | {r.validation_engines} | "
            f"{r.validation_rows} | {r.feature_count} | {r.rmse:.3f} | {r.mae:.3f} | "
            f"{r.nasa_score_sum:.3f} | {r.nasa_score_mean:.6f} | {r.fit_seconds:.1f} |"
        )
    lines += [
        "",
        "## Best validation RMSE per subset",
        "",
        "| Subset | Best validation model | RMSE | MAE | NASA score (sum) |",
        "|---|---|---:|---:|---:|",
    ]
    best = metrics.sort_values(["subset", "rmse", "mae"]).groupby("subset", as_index=False).first()
    for r in best.itertuples(index=False):
        lines.append(f"| {r.subset} | {r.model} | {r.rmse:.3f} | {r.mae:.3f} | {r.nasa_score_sum:.3f} |")
    lines += [
        "",
        "## Interpretation and limits",
        "",
        "- Validation engines are wholly separate from training engines; all models for a subset use the same split.",
        "- Fixed baseline settings were used; this is not a hyperparameter search.",
        "- This phase establishes internal validation baselines only. It does not evaluate official held-out test labels, prove superiority over published papers, or establish research novelty.",
        "- The standard official test targets remain untouched for the later frozen evaluation protocol.",
        "- The next steps are to review the nearest literature and protocol, then use these baselines as comparators for the Phase 6 adaptive ensemble.",
        "",
        "Machine-readable metrics and prediction files are under `results/phase5/` (local/ignored); trained model artifacts are under `models/phase5/` (local/ignored).",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rul_cap = None if args.rul_cap == 0 else args.rul_cap
    if rul_cap is not None and rul_cap < 1:
        raise ValueError("--rul-cap must be 0 (uncapped) or a positive integer")
    if args.trees < 10 or args.max_iter < 10:
        raise ValueError("Use at least 10 trees/iterations; defaults are 120 and 150")
    if not 0.05 <= args.validation_fraction <= 0.5:
        raise ValueError("--validation-fraction must be between 0.05 and 0.5")
    validate_inputs(args.data_dir, args.subsets)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    feature_counts: dict[str, int] = {}
    all_settings = {
        "project": "DARE-RUL",
        "phase": 5,
        "rul_cap": rul_cap,
        "rul_cap_note": "125 is a provisional primary benchmark setting; see phase5_protocol.md",
        "validation_fraction_by_engine": args.validation_fraction,
        "seed": args.seed,
        "models": {
            "RF": {"n_estimators": args.trees, "max_features": 0.7, "min_samples_leaf": 2},
            "HGB": {"max_iter": args.max_iter, "learning_rate": 0.08, "max_leaf_nodes": 31, "l2_regularization": 1.0, "early_stopping": False},
        },
        "official_test_targets_used": False,
        "results": [],
    }

    for subset in args.subsets:
        path = args.data_dir / subset / "train_features.parquet"
        print(f"[{subset}] loading Phase 4 training features: {path}", flush=True)
        frame = pd.read_parquet(path)
        if "engine_id" not in frame or "cycle" not in frame or "RUL" not in frame:
            raise ValueError(f"{subset}: feature file must contain engine_id, cycle and RUL columns")
        if frame.duplicated(["engine_id", "cycle"]).any():
            raise ValueError(f"{subset}: duplicate engine/cycle keys found")
        train_idx, val_idx = split_by_engine(frame, args.validation_fraction, args.seed)
        train_df = frame.iloc[train_idx].copy()
        val_df = frame.iloc[val_idx].copy()
        train_engines = sorted(train_df.engine_id.unique().tolist())
        val_engines = sorted(val_df.engine_id.unique().tolist())
        if set(train_engines) & set(val_engines):
            raise AssertionError(f"{subset}: engine overlap found between train and validation")
        y_train = capped_target(train_df, rul_cap)
        y_val = capped_target(val_df, rul_cap)
        subset_dir = args.models_dir / subset
        subset_dir.mkdir(parents=True, exist_ok=True)

        for window in (15, 30):
            feature_cols = select_feature_columns(frame, window)
            feature_counts[f"{subset}_w{window}"] = len(feature_cols)
            x_train = train_df[feature_cols].to_numpy(dtype=np.float32, copy=True)
            x_val = val_df[feature_cols].to_numpy(dtype=np.float32, copy=True)
            if not np.isfinite(x_train).all() or not np.isfinite(x_val).all():
                raise ValueError(f"{subset}/w{window}: non-finite model features found")

            for kind in ("RF", "HGB"):
                name = f"{kind}{window}"
                print(
                    f"  fitting {name}: {len(train_engines)} train engines / "
                    f"{len(val_engines)} validation engines / {len(feature_cols)} features",
                    flush=True,
                )
                model = build_regressor(kind, args.seed)
                # Allow command-line overrides of the documented compute budget.
                if kind == "RF":
                    model.set_params(n_estimators=args.trees)
                else:
                    model.set_params(max_iter=args.max_iter)
                started = time.perf_counter()
                model.fit(x_train, y_train)
                fit_seconds = time.perf_counter() - started
                y_pred = clipped_predictions(model.predict(x_val), rul_cap)
                scores = calculate_metrics(y_val, y_pred)
                metrics_rows.append({
                    "subset": subset, "model": name, "window": window,
                    "train_engines": len(train_engines), "validation_engines": len(val_engines),
                    "train_rows": len(train_df), "validation_rows": len(val_df),
                    "feature_count": len(feature_cols), "rul_cap": rul_cap,
                    "seed": args.seed, "fit_seconds": round(fit_seconds, 3), **scores,
                })
                pred_frame = val_df[["engine_id", "cycle"]].copy()
                pred_frame["subset"] = subset
                pred_frame["model"] = name
                pred_frame["RUL_true_capped"] = y_val
                pred_frame["RUL_pred"] = y_pred
                prediction_frames.append(pred_frame)

                artifact_path = subset_dir / f"{name}.joblib"
                joblib.dump(model, artifact_path, compress=3)
                (subset_dir / f"{name}_metadata.json").write_text(
                    json.dumps({"subset": subset, "model": name, "window": window,
                                "features": feature_cols, "rul_cap": rul_cap,
                                "seed": args.seed, "train_engines": train_engines,
                                "validation_engines": val_engines,
                                "artifact": str(artifact_path.relative_to(ROOT))}, indent=2),
                    encoding="utf-8",
                )
                all_settings["results"].append({"subset": subset, "model": name,
                                                 "feature_count": len(feature_cols),
                                                 "fit_seconds": round(fit_seconds, 3),
                                                 **scores})
                print(
                    f"    done in {fit_seconds:.1f}s | RMSE={scores['rmse']:.3f} "
                    f"MAE={scores['mae']:.3f} NASA-score={scores['nasa_score_sum']:.2f}",
                    flush=True,
                )
                del model
                gc.collect()
            del x_train, x_val

    metrics = pd.DataFrame(metrics_rows).sort_values(["subset", "model"]).reset_index(drop=True)
    metrics_path = args.results_dir / "validation_metrics.csv"
    predictions_path = args.results_dir / "validation_predictions.csv"
    metrics.to_csv(metrics_path, index=False)
    pd.concat(prediction_frames, ignore_index=True).to_csv(predictions_path, index=False)
    (args.results_dir / "run_metadata.json").write_text(json.dumps(all_settings, indent=2), encoding="utf-8")
    summary_path = ROOT / "docs" / "project" / "phase5_run_summary.md"
    write_summary(metrics, summary_path, rul_cap, args.seed, args.validation_fraction, feature_counts)
    print(f"\nPHASE 5 BASELINE RUN PASS. Metrics: {metrics_path}", flush=True)
    print(f"Validation predictions: {predictions_path}", flush=True)
    print(f"Curated summary: {summary_path}", flush=True)
    print("Official test RUL files were not loaded by this script.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
