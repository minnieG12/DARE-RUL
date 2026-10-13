"""Train an OOF-calibrated adaptive RUL ensemble and compare it on Phase 5 validation engines.

This script intentionally does not read test_FDxxx.txt or RUL_FDxxx.txt. It reuses
Phase 5's fixed engine split and validation predictions, and fits its adaptive gate
only from out-of-fold predictions on the Phase 5 training engines.
"""
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
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.phase5.baseline_core import (  # noqa: E402
    build_regressor,
    capped_target,
    select_feature_columns,
)
from scripts.phase6.ensemble_core import (  # noqa: E402
    EXPERTS,
    adaptive_blend,
    build_error_gate,
    build_validation_error_artifact,
    engine_balanced_sample_weights,
    engine_macro_metrics,
    inverse_error_weights,
    make_gate_features,
    metric_summary,
    static_inverse_mae_weights,
)

SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", type=Path, default=ROOT / "data" / "features" / "phase4")
    parser.add_argument("--phase5-results-dir", type=Path, default=ROOT / "results" / "phase5")
    parser.add_argument("--phase5-models-dir", type=Path, default=ROOT / "models" / "phase5")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results" / "phase6")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "models" / "phase6")
    parser.add_argument("--rul-cap", type=int, default=125)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--oof-folds", type=int, default=4)
    parser.add_argument("--subsets", nargs="+", choices=list(SUBSETS), default=list(SUBSETS))
    return parser.parse_args()


def load_phase5_metadata(models_dir: Path, subset: str) -> dict:
    path = models_dir / subset / "RF15_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing Phase 5 model metadata: {path}; complete Phase 5 first")
    meta = json.loads(path.read_text(encoding="utf-8"))
    if meta.get("subset") != subset:
        raise ValueError(f"{path}: subset does not match {subset}")
    if int(meta.get("rul_cap") or 0) != 125:
        raise ValueError(f"{subset}: Phase 5 model cap is not 125; run Phase 6 with matching protocol")
    train_engines = meta.get("train_engines")
    validation_engines = meta.get("validation_engines")
    if not isinstance(train_engines, list) or not isinstance(validation_engines, list):
        raise ValueError(f"{path}: missing train_engines/validation_engines lists")
    if set(train_engines) & set(validation_engines):
        raise AssertionError(f"{subset}: Phase 5 train/validation engine overlap")
    return meta


def check_phase5_predictions(predictions_path: Path, subset: str, validation_engines: list[int]) -> pd.DataFrame:
    if not predictions_path.exists():
        raise FileNotFoundError(f"Missing Phase 5 validation predictions: {predictions_path}; run Phase 5 first")
    all_predictions = pd.read_csv(predictions_path)
    required = {"subset", "model", "engine_id", "cycle", "RUL_true_capped", "RUL_pred"}
    missing = required - set(all_predictions.columns)
    if missing:
        raise ValueError(f"Phase 5 prediction file lacks columns: {sorted(missing)}")
    selected = all_predictions.loc[all_predictions.subset == subset].copy()
    selected = selected.loc[selected.model.isin(EXPERTS)]
    selected["engine_id"] = selected.engine_id.astype(int)
    selected["cycle"] = selected.cycle.astype(int)
    if set(selected.model.unique()) != set(EXPERTS):
        raise ValueError(f"{subset}: Phase 5 predictions do not contain all four experts")
    if set(selected.engine_id.unique()) != set(validation_engines):
        raise ValueError(f"{subset}: validation engine list differs from Phase 5 metadata")
    if selected.duplicated(["model", "engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate prediction key found")
    pred_wide = selected.pivot(index=["engine_id", "cycle", "RUL_true_capped"], columns="model", values="RUL_pred").reset_index()
    pred_wide.columns.name = None
    for column in EXPERTS:
        if column not in pred_wide:
            raise ValueError(f"{subset}: missing {column} validation predictions")
    if pred_wide[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: missing expert validation predictions")
    if pred_wide.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate merged validation key")
    return pred_wide.sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)


def run_oof_predictions(
    training: pd.DataFrame,
    cap: int,
    seed: int,
    n_splits: int,
    subset: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Generate engine-grouped out-of-fold expert predictions on Phase 5 train engines."""
    engine_count = training.engine_id.nunique()
    if engine_count < n_splits:
        raise ValueError(f"{subset}: {engine_count} train engines cannot support {n_splits} OOF folds")
    training = training.sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    groups = training.engine_id.to_numpy()
    y = capped_target(training, cap)
    oof = pd.DataFrame({"engine_id": training.engine_id, "cycle": training.cycle, "RUL_true_capped": y})
    for expert in EXPERTS:
        oof[expert] = np.nan
    fold_splitter = GroupKFold(n_splits=n_splits)
    for fold, (fit_idx, oof_idx) in enumerate(fold_splitter.split(training, y, groups=groups), start=1):
        fit_df = training.iloc[fit_idx]
        held_df = training.iloc[oof_idx]
        if set(fit_df.engine_id.unique()) & set(held_df.engine_id.unique()):
            raise AssertionError(f"{subset}: OOF fold {fold} has engine leakage")
        print(f"    OOF fold {fold}/{n_splits}: {fit_df.engine_id.nunique()} fit engines, {held_df.engine_id.nunique()} OOF engines", flush=True)
        for window in (15, 30):
            features = select_feature_columns(training, window)
            x_fit = fit_df[features].to_numpy(dtype=np.float32, copy=True)
            x_held = held_df[features].to_numpy(dtype=np.float32, copy=True)
            if not np.isfinite(x_fit).all() or not np.isfinite(x_held).all():
                raise ValueError(f"{subset}/fold{fold}/w{window}: non-finite features")
            for kind in ("RF", "HGB"):
                expert = f"{kind}{window}"
                estimator = build_regressor(kind, seed=seed)
                start = time.perf_counter()
                estimator.fit(x_fit, y[fit_idx])
                fold_pred = np.clip(estimator.predict(x_held), 0.0, float(cap))
                elapsed = time.perf_counter() - start
                oof.loc[oof_idx, expert] = fold_pred
                print(f"      {expert} OOF predictions complete ({elapsed:.1f}s)", flush=True)
                del estimator, fold_pred
                gc.collect()
            del x_fit, x_held
    if oof[list(EXPERTS)].isna().any().any():
        raise AssertionError(f"{subset}: OOF predictions have unfilled rows")
    return oof, select_feature_columns(training, 30)


def build_validation_context(
    subset_frame: pd.DataFrame,
    validation_predictions: pd.DataFrame,
    context_columns: list[str],
    cap: int,
    subset: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    val_feature_rows = subset_frame.loc[subset_frame.engine_id.isin(validation_predictions.engine_id.unique())].copy()
    val_feature_rows = val_feature_rows.sort_values(["engine_id", "cycle"], kind="stable")
    if val_feature_rows.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate Phase 4 validation feature keys")
    val = val_feature_rows.merge(
        validation_predictions,
        on=["engine_id", "cycle"],
        how="left",
        validate="one_to_one",
        suffixes=("_phase4", ""),
    )
    if val.RUL_true_capped.isna().any() or val[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: Phase 5 validation predictions did not align to Phase 4 features")
    expected_target = np.minimum(val["RUL"].to_numpy(dtype=float), cap)
    if not np.allclose(expected_target, val.RUL_true_capped.to_numpy(dtype=float)):
        raise ValueError(f"{subset}: Phase 5 capped validation labels do not match Phase 4 RUL")
    if not np.isfinite(val[context_columns].to_numpy(dtype=float)).all():
        raise ValueError(f"{subset}: non-finite validation context features")
    return val.reset_index(drop=True), val[context_columns].reset_index(drop=True)


def add_metrics_row(rows: list[dict], subset: str, method: str, y_true: np.ndarray,
                    predictions: np.ndarray, engine_ids: np.ndarray, model_type: str) -> None:
    scored = metric_summary(y_true, predictions)
    macro = engine_macro_metrics(engine_ids, y_true, predictions)
    rows.append({
        "subset": subset,
        "method": method,
        "method_type": model_type,
        "validation_rows": int(len(y_true)),
        "validation_engines": int(pd.Series(engine_ids).nunique()),
        **scored,
        **macro,
    })


def write_summary(metrics: pd.DataFrame, reliability: pd.DataFrame, path: Path,
                  cap: int, folds: int, seed: int) -> None:
    lines = [
        "# Phase 6 Run Summary — OOF-Calibrated Adaptive Ensemble",
        "",
        "- **Status:** PASS (adaptive ensemble fit and compared on Phase 5 validation engines)",
        f"- **RUL cap:** {cap} cycles (provisional, inherited from Phase 5)",
        f"- **OOF folds:** {folds}, grouped by engine on Phase 5 training engines only",
        f"- **Seed:** {seed}",
        "- **Experts:** RF15, HGB15, RF30 and HGB30; expert hyperparameters follow Phase 5.",
        "- **Ensemble comparators:** four individual experts, equal average, OOF engine-macro-MAE inverse-error weights, and adaptive per-row error gate.",
        "- **Adaptive gate:** estimates each expert's absolute error using OOF-only examples, context features and expert disagreement; converts predicted errors into per-row inverse-error weights.",
        "- **Official test RUL labels:** not read or used.",
        "",
        "## Validation results",
        "",
        "All metrics below use the same Phase 5 held-out validation engines and capped labels. Row-weighted metrics match Phase 5's evaluation unit. Engine-macro metrics average each engine equally, which helps reveal the effect of different trajectory lengths. Lower is better for all listed metrics.",
        "",
        "| Subset | Method | Type | Rows | Engines | RMSE | MAE | NASA score sum | NASA score mean | Engine-macro RMSE | Engine-macro MAE | Engine-macro NASA mean |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    method_order = {name: i for i, name in enumerate((*EXPERTS, "equal_average", "oof_inverse_mae", "adaptive_error_gate"))}
    sorted_metrics = metrics.assign(_order=metrics.method.map(method_order)).sort_values(["subset", "_order"])
    for r in sorted_metrics.itertuples(index=False):
        lines.append(
            f"| {r.subset} | {r.method} | {r.method_type} | {r.validation_rows} | {r.validation_engines} | "
            f"{r.rmse:.3f} | {r.mae:.3f} | {r.nasa_score_sum:.3f} | {r.nasa_score_mean:.6f} | "
            f"{r.engine_macro_rmse:.3f} | {r.engine_macro_mae:.3f} | {r.engine_macro_nasa_score_mean:.6f} |"
        )
    lines += ["", "## Training-only OOF reliability", "", "These engine-macro MAEs were calculated from cross-fitted predictions on Phase 5 training engines. They set static blend weights; the official test set was not involved.", "", "| Subset | Expert | OOF engine-macro MAE | Static weight |", "|---|---|---:|---:|"]
    for r in reliability.sort_values(["subset", "expert"]).itertuples(index=False):
        lines.append(f"| {r.subset} | {r.expert} | {r.oof_engine_macro_mae:.3f} | {r.static_weight:.4f} |")
    lines += [
        "", "## Interpretation and limitations", "",
        "- The adaptive gate is a candidate method, not a proven novel contribution. Its benefit must be judged against the individual experts and simple averaging on unseen engines.",
        "- The validation engines were not used for OOF expert or gate fitting; validation data were used only for comparison/reporting.",
        "- The gate's error targets are OOF absolute errors and its sample weights balance each engine during fitting.",
        "- Validation rows from an engine are correlated. Row-weighted scores are provided for Phase 5 comparability; engine-macro scores are reported alongside them.",
        "- Results are internal validation results, not official held-out test metrics and not evidence of distributed scalability.",
        "- Phase 1 literature review and protocol approval (including capped vs uncapped sensitivity) remain prerequisites for publication claims.",
        "", "Machine-readable artifacts are local/ignored under `results/phase6/`; gate models are under `models/phase6/`.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_subset(subset: str, args: argparse.Namespace) -> tuple[list[dict], list[dict], list[dict], dict]:
    print(f"\n[{subset}] load Phase 4 features and the saved Phase 5 split", flush=True)
    phase5_meta = load_phase5_metadata(args.phase5_models_dir, subset)
    phase4_path = args.features_dir / subset / "train_features.parquet"
    if not phase4_path.exists():
        raise FileNotFoundError(f"Missing {phase4_path}; run Phase 4 first")
    all_rows = pd.read_parquet(phase4_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    required = {"engine_id", "cycle", "RUL"}
    if not required.issubset(all_rows.columns):
        raise ValueError(f"{subset}: Phase 4 file missing columns {sorted(required - set(all_rows.columns))}")
    if all_rows.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate engine-cycle keys in Phase 4 features")
    train_engines = [int(x) for x in phase5_meta["train_engines"]]
    val_engines = [int(x) for x in phase5_meta["validation_engines"]]
    if set(train_engines) | set(val_engines) != set(all_rows.engine_id.unique()):
        raise ValueError(f"{subset}: Phase 5 split does not cover exactly the Phase 4 training engines")
    training = all_rows.loc[all_rows.engine_id.isin(train_engines)].copy()
    if set(training.engine_id.unique()) != set(train_engines):
        raise ValueError(f"{subset}: one or more Phase 5 training engines are missing from Phase 4 features")

    phase5_pred = check_phase5_predictions(args.phase5_results_dir / "validation_predictions.csv", subset, val_engines)
    val, context_val = build_validation_context(all_rows, phase5_pred, select_feature_columns(all_rows, 30), args.rul_cap, subset)
    validation_experts = val.loc[:, list(EXPERTS)].copy().reset_index(drop=True)
    y_val = val.RUL_true_capped.to_numpy(dtype=float)
    val_eng = val.engine_id.to_numpy(dtype=int)
    metrics_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []

    oof, context_columns = run_oof_predictions(training, args.rul_cap, args.seed, args.oof_folds, subset)
    y_oof = oof.RUL_true_capped.to_numpy(dtype=float)
    gate_oof_context = training.loc[:, context_columns].reset_index(drop=True)
    gate_oof = make_gate_features(gate_oof_context, oof.loc[:, list(EXPERTS)])
    gate_val = make_gate_features(context_val, validation_experts)
    row_weights = engine_balanced_sample_weights(oof.engine_id)

    oof_mae_by_engine: dict[str, float] = {}
    for expert in EXPERTS:
        per_engine_mae = (oof.assign(_abs_error=np.abs(oof[expert].to_numpy(dtype=float) - y_oof))
                          .groupby("engine_id", sort=False)["_abs_error"].mean())
        oof_mae_by_engine[expert] = float(per_engine_mae.mean())
    static_weights = static_inverse_mae_weights(oof_mae_by_engine, floor=0.5)
    reliability_rows = [{"subset": subset, "expert": name, "oof_engine_macro_mae": oof_mae_by_engine[name], "static_weight": static_weights[name]} for name in EXPERTS]

    expected_error_cols: dict[str, np.ndarray] = {}
    subset_model_dir = args.models_dir / subset
    subset_model_dir.mkdir(parents=True, exist_ok=True)
    for expert in EXPERTS:
        error_target = np.abs(oof[expert].to_numpy(dtype=float) - y_oof)
        gate_model = build_error_gate(args.seed)
        print(f"    fitting adaptive error gate for {expert} on OOF errors", flush=True)
        gate_model.fit(gate_oof.to_numpy(dtype=np.float32), error_target, sample_weight=row_weights)
        predicted_err = np.maximum(gate_model.predict(gate_val.to_numpy(dtype=np.float32)), 0.0)
        expected_error_cols[expert] = predicted_err
        joblib.dump(gate_model, subset_model_dir / f"error_gate_{expert}.joblib", compress=3)
        del gate_model
        gc.collect()
    expected_errors = pd.DataFrame(expected_error_cols)
    adaptive_pred, adaptive_weights = adaptive_blend(validation_experts, expected_errors, error_floor=0.5)
    equal_pred = validation_experts.loc[:, list(EXPERTS)].mean(axis=1).to_numpy(dtype=float)
    static_pred = validation_experts.loc[:, list(EXPERTS)].to_numpy(dtype=float) @ np.asarray([static_weights[n] for n in EXPERTS])
    method_predictions: dict[str, tuple[np.ndarray, str]] = {name: (validation_experts[name].to_numpy(dtype=float), "individual_expert") for name in EXPERTS}
    method_predictions["equal_average"] = (equal_pred, "fixed_ensemble")
    method_predictions["oof_inverse_mae"] = (static_pred, "fixed_ensemble_train_only_weights")
    method_predictions["adaptive_error_gate"] = (adaptive_pred, "adaptive_ensemble_candidate")

    # Cross-check that the validation predictions from the Phase 5 experts are exactly the ones scored by Phase 5.
    for method, (pred, method_type) in method_predictions.items():
        add_metrics_row(metrics_rows, subset, method, y_val, pred, val_eng, method_type)
        pred_frame = pd.DataFrame({
            "subset": subset,
            "method": method,
            "engine_id": val.engine_id.to_numpy(dtype=int),
            "cycle": val.cycle.to_numpy(dtype=int),
            "RUL_true_capped": y_val,
            "RUL_pred": pred,
        })
        if method == "adaptive_error_gate":
            pred_frame = pd.concat([pred_frame, adaptive_weights.reset_index(drop=True)], axis=1)
        prediction_frames.append(pred_frame)

    oof_path = args.results_dir / subset / "oof_predictions.csv"
    oof_path.parent.mkdir(parents=True, exist_ok=True)
    oof.to_csv(oof_path, index=False)
    # Expected errors were predicted for held-out validation rows, so their keys
    # must come from `val`, not `oof` (which contains the larger training set).
    validation_error_artifact = build_validation_error_artifact(
        subset, val.loc[:, ["engine_id", "cycle"]], expected_errors
    )
    validation_error_artifact.to_csv(
        args.results_dir / subset / "adaptive_expected_errors_validation.csv", index=False
    )
    weight_doc = {"subset": subset, "oof_engine_macro_mae": oof_mae_by_engine,
                  "static_inverse_mae_weights": static_weights,
                  "adaptive_gate": "HistGradientBoostingRegressor predicts absolute expert error from 30-cycle context, expert predictions, spread and disagreement features.",
                  "adaptive_weight_rule": "normalized inverse max(predicted_abs_error, 0) plus 0.5 error floor"}
    (subset_model_dir / "ensemble_weights.json").write_text(json.dumps(weight_doc, indent=2), encoding="utf-8")
    subset_info = {
        "subset": subset,
        "train_engines": len(train_engines),
        "validation_engines": len(val_engines),
        "validation_rows": int(len(val)),
        "oof_train_engines": int(training.engine_id.nunique()),
        "oof_rows": int(len(oof)),
        "oof_folds": args.oof_folds,
        "experts": list(EXPERTS),
        "official_test_targets_used": False,
        "static_weights": static_weights,
        "status": "PASS",
    }
    print(f"[{subset}] PASS — {len(val)} validation rows, {len(val_engines)} held-out engines; adaptive gate evaluated", flush=True)
    return metrics_rows, prediction_frames, reliability_rows, subset_info


def main() -> int:
    args = parse_args()
    if args.rul_cap != 125:
        raise ValueError("This Phase 6 package expects the completed Phase 5 run with cap=125; resolve protocol changes before using another cap")
    if args.oof_folds < 3 or args.oof_folds > 5:
        raise ValueError("OOF folds must be between 3 and 5")
    if not (args.phase5_results_dir / "validation_predictions.csv").exists():
        raise FileNotFoundError("Phase 5 validation predictions missing; complete Phase 5 first")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    metric_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    reliability_rows: list[dict] = []
    subset_summaries: list[dict] = []
    for subset in args.subsets:
        m_rows, p_frames, r_rows, info = run_subset(subset, args)
        metric_rows.extend(m_rows)
        prediction_frames.extend(p_frames)
        reliability_rows.extend(r_rows)
        subset_summaries.append(info)
    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    reliability = pd.DataFrame(reliability_rows)
    if len(metrics) != len(args.subsets) * 7:
        raise AssertionError(f"Expected {len(args.subsets) * 7} metric rows, got {len(metrics)}")
    if predictions.RUL_pred.isna().any() or not np.isfinite(predictions.RUL_pred.to_numpy(dtype=float)).all():
        raise AssertionError("Validation predictions contain NaN or infinite values")
    metrics.to_csv(args.results_dir / "validation_metrics.csv", index=False)
    predictions.to_csv(args.results_dir / "validation_predictions.csv", index=False)
    reliability.to_csv(args.results_dir / "oof_reliability.csv", index=False)
    metadata = {
        "project": "DARE-RUL", "phase": 6, "status": "PASS",
        "rul_cap": args.rul_cap, "seed": args.seed, "oof_folds": args.oof_folds,
        "experts": list(EXPERTS),
        "methods": [*EXPERTS, "equal_average", "oof_inverse_mae", "adaptive_error_gate"],
        "official_test_targets_used": False,
        "gate_fit_data": "OOF expert absolute errors from Phase 5 training engines only; engine-balanced sample weights",
        "validation_source": "fixed Phase 5 engine-separated validation predictions and corresponding Phase 4 feature rows",
        "subsets": subset_summaries,
        "warning": "A successful run does not establish novelty; compare against literature and perform ablations before publication claims.",
    }
    (args.results_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_summary(metrics, reliability, ROOT / "docs" / "project" / "phase6_run_summary.md", args.rul_cap, args.oof_folds, args.seed)
    print("\nPHASE 6 ADAPTIVE ENSEMBLE RUN PASS", flush=True)
    print(f"Metrics: {args.results_dir / 'validation_metrics.csv'}", flush=True)
    print(f"Predictions: {args.results_dir / 'validation_predictions.csv'}", flush=True)
    print(f"Summary: {ROOT / 'docs' / 'project' / 'phase6_run_summary.md'}", flush=True)
    print("Official test RUL files were not loaded.", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
