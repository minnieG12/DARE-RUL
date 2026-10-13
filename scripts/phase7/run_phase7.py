"""Run DARE-RUL Phase 7: feature ablations, robustness, explainability and inference scaling.

Uses only Phase 4 train features, Phase 5's frozen engine split/predictions, and
Phase 6's OOF expert predictions. It never opens test_FDxxx.txt or RUL_FDxxx.txt.
Validation results are exploratory because the same held-out validation engines
were already used in Phase 5/6. Final official test results must remain a later,
frozen evaluation.
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase5.baseline_core import capped_target  # noqa: E402
from scripts.phase6.ensemble_core import (  # noqa: E402
    EXPERTS,
    adaptive_blend,
    build_error_gate,
    engine_balanced_sample_weights,
    engine_macro_metrics,
    metric_summary,
)
from scripts.phase7.phase7_core import (  # noqa: E402
    blend_with_gates,
    cross_window_features,
    enhanced_context,
    gate_expected_errors,
    meta_features,
    multiresolution_context,
    perturb_sensor_context,
    permutable_feature_groups,
)

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
VARIANTS = {
    "multires_gate": {"enhanced": False, "disagreement": True},
    "cross_window_gate": {"enhanced": True, "disagreement": True},
    "cross_window_no_disagreement": {"enhanced": True, "disagreement": False},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--features-dir", type=Path, default=ROOT / "data" / "features" / "phase4")
    p.add_argument("--phase5-models-dir", type=Path, default=ROOT / "models" / "phase5")
    p.add_argument("--phase5-results-dir", type=Path, default=ROOT / "results" / "phase5")
    p.add_argument("--phase6-results-dir", type=Path, default=ROOT / "results" / "phase6")
    p.add_argument("--results-dir", type=Path, default=ROOT / "results" / "phase7")
    p.add_argument("--models-dir", type=Path, default=ROOT / "models" / "phase7")
    p.add_argument("--rul-cap", type=int, default=125)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bootstrap-repeats", type=int, default=1000)
    p.add_argument("--permutation-repeats", type=int, default=2)
    p.add_argument("--noise-repeats", type=int, default=3)
    return p.parse_args()


def read_phase5_metadata(models_dir: Path, subset: str) -> dict:
    path = models_dir / subset / "RF15_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; complete Phase 5 before Phase 7")
    meta = json.loads(path.read_text(encoding="utf-8"))
    if meta.get("subset") != subset or int(meta.get("rul_cap") or 0) != 125:
        raise ValueError(f"{subset}: Phase 5 metadata is incompatible with the Phase 6 run (expected cap 125)")
    train_engines = set(map(int, meta.get("train_engines", [])))
    val_engines = set(map(int, meta.get("validation_engines", [])))
    if not train_engines or not val_engines or train_engines & val_engines:
        raise ValueError(f"{subset}: invalid or overlapping train/validation engine lists")
    return meta


def read_phase5_validation_predictions(path: Path, subset: str, validation_engines: set[int]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing Phase 5 predictions: {path}")
    frame = pd.read_csv(path)
    need = {"subset", "model", "engine_id", "cycle", "RUL_true_capped", "RUL_pred"}
    missing = need - set(frame.columns)
    if missing:
        raise ValueError(f"Phase 5 predictions missing columns: {sorted(missing)}")
    frame = frame.loc[(frame.subset == subset) & frame.model.isin(EXPERTS)].copy()
    frame["engine_id"] = frame.engine_id.astype(int)
    frame["cycle"] = frame.cycle.astype(int)
    if set(frame.model.unique()) != set(EXPERTS):
        raise ValueError(f"{subset}: Phase 5 predictions do not include all four experts")
    if set(frame.engine_id.unique()) != validation_engines:
        raise ValueError(f"{subset}: validation engines differ from the frozen Phase 5 split")
    if frame.duplicated(["model", "engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate Phase 5 validation prediction keys")
    targets = frame.groupby(["engine_id", "cycle"], as_index=False).RUL_true_capped.first()
    wide = frame.pivot(index=["engine_id", "cycle"], columns="model", values="RUL_pred").reset_index()
    wide.columns.name = None
    result = wide.merge(targets, on=["engine_id", "cycle"], validate="one_to_one")
    result = result.sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    if result[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: missing expert prediction after pivot")
    return result


def build_eval_data(subset: str, args: argparse.Namespace) -> dict:
    meta = read_phase5_metadata(args.phase5_models_dir, subset)
    feature_path = args.features_dir / subset / "train_features.parquet"
    if not feature_path.exists():
        raise FileNotFoundError(f"Missing Phase 4 training features: {feature_path}")
    all_rows = pd.read_parquet(feature_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    if all_rows.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate Phase 4 engine-cycle key")
    if not {"RUL", "engine_id", "cycle"}.issubset(all_rows.columns):
        raise ValueError(f"{subset}: Phase 4 feature file lacks target or join keys")
    train_engines = set(map(int, meta["train_engines"]))
    val_engines = set(map(int, meta["validation_engines"]))
    all_engines = set(map(int, all_rows.engine_id.unique()))
    if train_engines | val_engines != all_engines:
        raise ValueError(f"{subset}: Phase 5 split does not cover Phase 4 training engines")

    oof_path = args.phase6_results_dir / subset / "oof_predictions.csv"
    if not oof_path.exists():
        raise FileNotFoundError(f"Missing Phase 6 OOF predictions: {oof_path}; complete Phase 6 first")
    oof_raw = pd.read_csv(oof_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    oof_raw["engine_id"] = oof_raw.engine_id.astype(int)
    oof_raw["cycle"] = oof_raw.cycle.astype(int)
    if oof_raw.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{subset}: duplicate OOF prediction keys")
    if set(oof_raw.engine_id.unique()) != train_engines:
        raise ValueError(f"{subset}: OOF records do not match Phase 5 training engines")
    train_rows = all_rows.loc[all_rows.engine_id.isin(train_engines)].copy()
    oof = oof_raw.merge(train_rows, on=["engine_id", "cycle"], how="left", validate="one_to_one", suffixes=("", "_feature"))
    if oof.RUL.isna().any():
        raise ValueError(f"{subset}: some OOF rows failed to align to Phase 4 features")
    expected_y = np.minimum(oof.RUL.to_numpy(dtype=float), args.rul_cap)
    if not np.allclose(expected_y, oof.RUL_true_capped.to_numpy(dtype=float)):
        raise ValueError(f"{subset}: OOF targets do not match capped Phase 4 targets")
    if oof[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: incomplete OOF expert predictions")

    phase5_val = read_phase5_validation_predictions(args.phase5_results_dir / "validation_predictions.csv", subset, val_engines)
    val_rows = all_rows.loc[all_rows.engine_id.isin(val_engines)].copy()
    val = val_rows.merge(phase5_val, on=["engine_id", "cycle"], how="left", validate="one_to_one", suffixes=("_feature", ""))
    if val.RUL_true_capped.isna().any() or val[list(EXPERTS)].isna().any().any():
        raise ValueError(f"{subset}: validation feature/prediction alignment failed")
    if not np.allclose(np.minimum(val.RUL.to_numpy(dtype=float), args.rul_cap), val.RUL_true_capped.to_numpy(dtype=float)):
        raise ValueError(f"{subset}: validation targets do not match the Phase 5 cap")
    return {"subset": subset, "meta": meta, "all_rows": all_rows, "train_rows": train_rows,
            "oof": oof, "val": val, "train_engines": train_engines, "val_engines": val_engines}


def metric_row(subset: str, method: str, y: np.ndarray, pred: np.ndarray, engines: np.ndarray, method_type: str) -> dict:
    return {"subset": subset, "method": method, "method_type": method_type,
            "validation_rows": int(len(y)), "validation_engines": int(pd.Series(engines).nunique()),
            **metric_summary(y, pred), **engine_macro_metrics(engines, y, pred)}


def run_variant(subset_data: dict, variant: str, args: argparse.Namespace) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset = subset_data["subset"]
    oof = subset_data["oof"].sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    val = subset_data["val"].sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    cfg = VARIANTS[variant]
    if cfg["enhanced"]:
        ctx_oof = enhanced_context(oof, add_cross_window=True)
        ctx_val = enhanced_context(val, add_cross_window=True)
    else:
        ctx_oof = multiresolution_context(oof)
        ctx_val = multiresolution_context(val)
    pred_oof = oof.loc[:, list(EXPERTS)].reset_index(drop=True)
    pred_val = val.loc[:, list(EXPERTS)].reset_index(drop=True)
    X_oof = meta_features(ctx_oof, pred_oof, include_disagreement=cfg["disagreement"])
    X_val = meta_features(ctx_val, pred_val, include_disagreement=cfg["disagreement"])
    if list(X_oof.columns) != list(X_val.columns):
        raise AssertionError(f"{subset}/{variant}: OOF and validation meta-feature columns differ")
    y_oof = oof.RUL_true_capped.to_numpy(dtype=float)
    y_val = val.RUL_true_capped.to_numpy(dtype=float)
    sample_weights = engine_balanced_sample_weights(oof.engine_id)
    gate_models: dict[str, object] = {}
    expected_errors: dict[str, np.ndarray] = {}
    model_dir = args.models_dir / subset
    model_dir.mkdir(parents=True, exist_ok=True)
    for expert in EXPERTS:
        error_target = np.abs(oof[expert].to_numpy(dtype=float) - y_oof)
        gate = build_error_gate(seed=args.seed)
        gate.fit(X_oof.to_numpy(dtype=np.float32), error_target, sample_weight=sample_weights)
        expected_errors[expert] = np.maximum(gate.predict(X_val.to_numpy(dtype=np.float32)), 0.0)
        gate_models[expert] = gate
        joblib.dump(gate, model_dir / f"gate_{variant}_{expert}.joblib", compress=3)
        del gate
        gc.collect()
    errors_frame = pd.DataFrame(expected_errors)
    blend, weights = adaptive_blend(pred_val, errors_frame, error_floor=0.5)
    method = {"multires_gate": "multires_error_gate", "cross_window_gate": "cross_window_error_gate",
              "cross_window_no_disagreement": "cross_window_no_disagreement"}[variant]
    mrow = metric_row(subset, method, y_val, blend, val.engine_id.to_numpy(dtype=int), "phase7_feature_ablation_candidate")
    predictions = pd.DataFrame({"subset": subset, "method": method, "engine_id": val.engine_id.to_numpy(dtype=int),
                                "cycle": val.cycle.to_numpy(dtype=int), "RUL_true_capped": y_val, "RUL_pred": blend})
    predictions = pd.concat([predictions, weights.reset_index(drop=True)], axis=1)
    err_export = pd.DataFrame({"subset": subset, "engine_id": val.engine_id.to_numpy(dtype=int), "cycle": val.cycle.to_numpy(dtype=int),
                               **{f"expected_error_{e}": errors_frame[e].to_numpy() for e in EXPERTS}})
    specification = {"subset": subset, "variant": variant, "context_columns": list(ctx_oof.columns),
                     "meta_feature_columns": list(X_oof.columns), "context_feature_count": len(ctx_oof.columns),
                     "meta_feature_count": len(X_oof.columns), "include_cross_window_features": bool(cfg["enhanced"]),
                     "include_explicit_disagreement_features": bool(cfg["disagreement"]),
                     "engine_id_cycle_RUL_excluded_from_meta_inputs": True}
    spec_dir = args.results_dir / subset
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / f"feature_spec_{variant}.json").write_text(json.dumps(specification, indent=2), encoding="utf-8")
    return {"variant": variant, "method": method, "context_oof": ctx_oof, "context_val": ctx_val,
            "X_oof": X_oof, "X_val": X_val, "pred_val": pred_val, "y_val": y_val,
            "gate_models": gate_models, "metrics": mrow, "predictions": predictions, "errors": err_export,
            "feature_spec": specification}


def per_engine_metric_vectors(frame: pd.DataFrame) -> tuple[list[int], dict[str, np.ndarray]]:
    ids: list[int] = []
    rmse: list[float] = []
    mae: list[float] = []
    nasa: list[float] = []
    for engine, g in frame.groupby("engine_id", sort=True):
        m = metric_summary(g.RUL_true_capped.to_numpy(dtype=float), g.RUL_pred.to_numpy(dtype=float))
        ids.append(int(engine)); rmse.append(m["rmse"]); mae.append(m["mae"]); nasa.append(m["nasa_score_mean"])
    return ids, {"engine_macro_rmse": np.asarray(rmse), "engine_macro_mae": np.asarray(mae),
                 "engine_macro_nasa_score_mean": np.asarray(nasa)}


def paired_bootstrap(metrics_preds: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict] = []
    compare_to = ("adaptive_error_gate", "equal_average", "HGB30")
    metric_names = ("engine_macro_rmse", "engine_macro_mae", "engine_macro_nasa_score_mean")
    rng = np.random.default_rng(args.seed + 700)
    for subset in SUBSETS:
        sub = metrics_preds.loc[metrics_preds.subset == subset]
        by_method = {m: sub.loc[sub.method == m].copy() for m in ("cross_window_error_gate", *compare_to)}
        for method, frame in by_method.items():
            if frame.empty:
                raise ValueError(f"{subset}: missing method {method} needed for paired bootstrap")
        keys_by_method: dict[str, tuple[list[int], dict[str, np.ndarray]]] = {m: per_engine_metric_vectors(f) for m, f in by_method.items()}
        ids = keys_by_method["cross_window_error_gate"][0]
        for comp in compare_to:
            if keys_by_method[comp][0] != ids:
                raise ValueError(f"{subset}: cannot pair bootstrap because engine IDs differ for {comp}")
            for metric in metric_names:
                cand = keys_by_method["cross_window_error_gate"][1][metric]
                base = keys_by_method[comp][1][metric]
                delta = cand - base
                draws = np.empty(args.bootstrap_repeats, dtype=float)
                for b in range(args.bootstrap_repeats):
                    sample = rng.integers(0, len(delta), size=len(delta))
                    draws[b] = float(np.mean(delta[sample]))
                low, high = np.quantile(draws, [0.025, 0.975])
                rows.append({"subset": subset, "candidate": "cross_window_error_gate", "comparator": comp,
                             "metric": metric, "difference_candidate_minus_comparator": float(delta.mean()),
                             "ci95_low": float(low), "ci95_high": float(high),
                             "bootstrap_repeats": int(args.bootstrap_repeats),
                             "interpretation": "candidate lower" if high < 0 else ("comparator lower" if low > 0 else "CI overlaps zero")})
    return pd.DataFrame(rows)


def robustness_noise(eval_data: dict, cross_result: dict, args: argparse.Namespace) -> pd.DataFrame:
    subset = eval_data["subset"]
    # Noise the direct Phase 4 context first, then recompute engineered contrasts.
    base_val = multiresolution_context(eval_data["val"].sort_values(["engine_id", "cycle"], kind="stable"))
    train_context = multiresolution_context(eval_data["oof"].sort_values(["engine_id", "cycle"], kind="stable"))
    pred_val = cross_result["pred_val"]
    gates = cross_result["gate_models"]
    rows: list[dict] = []
    trials = [(0.0, 0)] + [(level, rep) for level in (0.01, 0.05) for rep in range(1, args.noise_repeats + 1)]
    for level, rep in trials:
        noisy_base = perturb_sensor_context(base_val, train_context, level, seed=args.seed + int(level * 10000) + rep + sum(ord(c) for c in subset))
        if level > 0:
            ctx = pd.concat([noisy_base, cross_window_features(noisy_base)], axis=1)
        else:
            ctx = cross_result["context_val"].copy()
        X = meta_features(ctx, pred_val, include_disagreement=True)
        err = gate_expected_errors(gates, X)
        blend, _ = adaptive_blend(pred_val, err, error_floor=0.5)
        y = eval_data["val"].sort_values(["engine_id", "cycle"], kind="stable").RUL_true_capped.to_numpy(dtype=float)
        engines = eval_data["val"].sort_values(["engine_id", "cycle"], kind="stable").engine_id.to_numpy(dtype=int)
        rows.append({"subset": subset, "variant": "cross_window_error_gate", "sensor_feature_noise_fraction_of_training_sd": level,
                     "repeat": rep, **metric_summary(y, blend), **engine_macro_metrics(engines, y, blend),
                     "note": "Synthetic perturbation of sensor-derived feature columns at inference; not a physical sensor-fault simulation."})
    return pd.DataFrame(rows)


def feature_group_permutation(eval_data: dict, cross_result: dict, args: argparse.Namespace) -> pd.DataFrame:
    subset = eval_data["subset"]
    X = cross_result["X_val"].reset_index(drop=True)
    pred = cross_result["pred_val"].reset_index(drop=True)
    val = eval_data["val"].sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    y = val.RUL_true_capped.to_numpy(dtype=float)
    engines = val.engine_id.to_numpy(dtype=int)
    gates = cross_result["gate_models"]
    base_errors = gate_expected_errors(gates, X)
    base_pred, _ = adaptive_blend(pred, base_errors)
    base_metrics = engine_macro_metrics(engines, y, base_pred)
    groups = permutable_feature_groups(X)
    rng = np.random.default_rng(args.seed + 900 + sum(ord(c) for c in subset))
    rows: list[dict] = []
    for name, cols in groups.items():
        deltas = []
        for rep in range(1, args.permutation_repeats + 1):
            order = rng.permutation(len(X))
            changed = X.copy()
            changed.loc[:, cols] = X.loc[order, cols].to_numpy()
            err = gate_expected_errors(gates, changed)
            p, _ = adaptive_blend(pred, err)
            mm = engine_macro_metrics(engines, y, p)
            deltas.append({"delta_engine_macro_rmse": mm["engine_macro_rmse"] - base_metrics["engine_macro_rmse"],
                           "delta_engine_macro_mae": mm["engine_macro_mae"] - base_metrics["engine_macro_mae"],
                           "delta_engine_macro_nasa_score_mean": mm["engine_macro_nasa_score_mean"] - base_metrics["engine_macro_nasa_score_mean"]})
        rows.append({"subset": subset, "feature_group": name, "feature_count": len(cols), "permutation_repeats": args.permutation_repeats,
                     "baseline_engine_macro_rmse": base_metrics["engine_macro_rmse"],
                     "baseline_engine_macro_mae": base_metrics["engine_macro_mae"],
                     **{k: float(np.mean([d[k] for d in deltas])) for k in ("delta_engine_macro_rmse", "delta_engine_macro_mae", "delta_engine_macro_nasa_score_mean")},
                     "interpretation": "positive delta means permuting this group worsened the score on this validation split"})
    return pd.DataFrame(rows)


def inference_benchmark(eval_data: dict, cross_result: dict) -> pd.DataFrame:
    subset = eval_data["subset"]
    X = cross_result["X_val"].reset_index(drop=True)
    pred = cross_result["pred_val"].reset_index(drop=True)
    gates = cross_result["gate_models"]
    rows: list[dict] = []
    # Warm-up small batch, then time increasing copies of validation rows.
    warm = X.iloc[: min(128, len(X))]
    _ = gate_expected_errors(gates, warm)
    for multiplier in (1, 2, 5):
        xx = pd.concat([X] * multiplier, ignore_index=True)
        pp = pd.concat([pred] * multiplier, ignore_index=True)
        start = time.perf_counter()
        errs = gate_expected_errors(gates, xx)
        blend, _ = adaptive_blend(pp, errs)
        elapsed = max(time.perf_counter() - start, 1e-9)
        if len(blend) != len(xx):
            raise AssertionError("Inference benchmark lost rows")
        rows.append({"subset": subset, "multiplier": multiplier, "rows_processed": int(len(xx)),
                     "meta_feature_count": int(xx.shape[1]), "elapsed_seconds": float(elapsed),
                     "rows_per_second": float(len(xx) / elapsed),
                     "scope_note": "Local in-process CPU inference benchmark on repeated validation rows; not distributed Spark/Kafka scalability evidence."})
        del xx, pp, errs, blend
        gc.collect()
    return pd.DataFrame(rows)


def write_summary(metrics: pd.DataFrame, noise: pd.DataFrame, bootstrap: pd.DataFrame,
                  importance: pd.DataFrame, inference: pd.DataFrame, path: Path,
                  seed: int, cap: int) -> None:
    lines = [
        "# Phase 7 Run Summary — Ablation, Robustness, Explainability and Inference Scaling", "",
        "- **Status:** PASS (all analysis outputs generated)",
        f"- **RUL cap:** {cap} cycles (provisional; Phase 1 protocol decision remains open)",
        f"- **Seed:** {seed}",
        "- **Official test RUL files:** not loaded or used.",
        "- **Main feature addition:** 84 cross-window sensor features (21 sensors × 4 contrasts) derived from causal 15/30-cycle statistics.",
        "- **New gate variants:** multi-resolution context; multi-resolution plus cross-window engineered contrasts; enhanced context without explicit disagreement summaries.",
        "- **Interpretation guardrail:** Phase 7 uses the existing Phase 5/6 validation engines for exploratory ablations. Do not present these results as an independent final test.", "",
        "## Best validation RMSE per subset", "", "| Subset | Best method on this validation split | RMSE | MAE | Engine-macro MAE |", "|---|---|---:|---:|---:|"
    ]
    for subset in SUBSETS:
        s = metrics.loc[metrics.subset == subset].sort_values("rmse")
        if not s.empty:
            r = s.iloc[0]
            lines.append(f"| {subset} | {r.method} | {float(r.rmse):.3f} | {float(r.mae):.3f} | {float(r.engine_macro_mae):.3f} |")
    lines += ["", "## Feature-ablation methods", "", "The combined metrics CSV includes the seven Phase 6 methods and three Phase 7 gates. Compare `multires_error_gate`, `cross_window_error_gate`, and `cross_window_no_disagreement` with `adaptive_error_gate`, `equal_average`, and the single experts. Lower errors are better; do not infer a universal win from one subset or metric.", "",
              "## Paired engine bootstrap", "", "`paired_bootstrap.csv` reports the cross-window gate minus selected comparators for engine-macro metrics. Negative differences favour the cross-window gate. Confidence intervals are conditional on this fixed validation cohort and are not an external test result.", "",
              "## Sensor-feature noise stress test", "", "`noise_robustness.csv` perturbs sensor-derived input feature columns by 1% and 5% of training-feature standard deviations at inference. This is a synthetic feature perturbation, not a validated physical sensor-fault model.", "",
              "## Group-permutation explainability", "", "`feature_group_importance.csv` measures how much validation performance changes when each input group is permuted. Positive deltas mean the score worsened after permutation, suggesting the group contributes useful signal on this validation split. This is a post-hoc diagnostic, not causal evidence.", "",
              "## Inference benchmark", "", "`inference_benchmark.csv` times local in-process gate inference for 1×, 2× and 5× repeated validation rows. It is a CPU inference microbenchmark only; it does not demonstrate distributed Spark/Kafka/HDFS throughput or fault recovery.", "",
              "## Remaining limitations", "", "- This run does not load official test labels.", "- The validation set has already informed Phase 5/6 model comparison and is reused for Phase 7 exploratory ablations; do not continue tuning against it indefinitely.", "- RUL cap 125 remains provisional until Phase 1 literature review and protocol approval are complete.", "- Novelty, superiority, distributed scalability and real-aircraft generalization are not established by a successful run.", "",
              "Generated files are local/ignored under `results/phase7/`; fitted gates are under `models/phase7/`."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.rul_cap != 125:
        raise ValueError("Phase 7 is aligned to Phase 5/6 cap=125; settle protocol changes before a different cap")
    if args.bootstrap_repeats < 200:
        raise ValueError("Use at least 200 paired bootstrap repeats")
    if args.permutation_repeats < 1 or args.noise_repeats < 1:
        raise ValueError("Permutation and noise repeat counts must be positive")
    phase6_metric_path = args.phase6_results_dir / "validation_metrics.csv"
    phase6_pred_path = args.phase6_results_dir / "validation_predictions.csv"
    if not phase6_metric_path.exists() or not phase6_pred_path.exists():
        raise FileNotFoundError("Phase 6 metrics/predictions missing; complete Phase 6 first")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    base_metrics = pd.read_csv(phase6_metric_path)
    base_predictions = pd.read_csv(phase6_pred_path)
    if len(base_metrics) != 28:
        raise ValueError(f"Expected 28 Phase 6 metrics; found {len(base_metrics)}")
    if base_predictions.RUL_pred.isna().any() or not np.isfinite(base_predictions.RUL_pred.to_numpy(dtype=float)).all():
        raise ValueError("Phase 6 validation predictions contain invalid values")
    for col in ("subset", "method", "engine_id", "cycle", "RUL_true_capped", "RUL_pred"):
        if col not in base_predictions.columns:
            raise ValueError(f"Phase 6 prediction file missing required column {col}")

    all_metrics: list[pd.DataFrame] = [base_metrics]
    new_predictions: list[pd.DataFrame] = []
    all_errors: list[pd.DataFrame] = []
    noise_tables: list[pd.DataFrame] = []
    importance_tables: list[pd.DataFrame] = []
    inference_tables: list[pd.DataFrame] = []
    subset_summary: list[dict] = []

    for subset in SUBSETS:
        print(f"\n[Phase 7/{subset}] prepare OOF and validation rows", flush=True)
        data = build_eval_data(subset, args)
        new_metric_rows = []
        subset_variants: dict[str, dict] = {}
        for variant in VARIANTS:
            print(f"  fit enhanced gate variant: {variant}", flush=True)
            result = run_variant(data, variant, args)
            subset_variants[variant] = result
            new_metric_rows.append(result["metrics"])
            new_predictions.append(result["predictions"])
            if variant == "cross_window_gate":
                all_errors.append(result["errors"])
                print("  robustness: sensor-feature noise stress test", flush=True)
                noise_tables.append(robustness_noise(data, result, args))
                print("  explainability: group permutation analysis", flush=True)
                importance_tables.append(feature_group_permutation(data, result, args))
                print("  timing: local inference scale benchmark", flush=True)
                inference_tables.append(inference_benchmark(data, result))
        all_metrics.append(pd.DataFrame(new_metric_rows))
        subset_summary.append({"subset": subset, "train_engines": len(data["train_engines"]),
                               "validation_engines": len(data["val_engines"]),
                               "validation_rows": int(len(data["val"])), "oof_rows": int(len(data["oof"])),
                               "variants": list(VARIANTS), "official_test_targets_used": False, "status": "PASS"})

    metrics = pd.concat(all_metrics, ignore_index=True, sort=False)
    predictions = pd.concat([base_predictions, *new_predictions], ignore_index=True, sort=False)
    if len(metrics) != 40:
        raise AssertionError(f"Expected 40 metric rows (10 methods × 4 subsets), got {len(metrics)}")
    if set(metrics.subset.unique()) != set(SUBSETS):
        raise AssertionError("Phase 7 metrics do not cover all four subsets")
    for subset in SUBSETS:
        if int((metrics.subset == subset).sum()) != 10:
            raise AssertionError(f"{subset}: expected 10 method rows")
    if predictions.RUL_pred.isna().any() or not np.isfinite(predictions.RUL_pred.to_numpy(dtype=float)).all():
        raise AssertionError("Combined validation predictions contain NaN/infinity")

    metrics.to_csv(args.results_dir / "validation_metrics.csv", index=False)
    predictions.to_csv(args.results_dir / "validation_predictions.csv", index=False)
    ablation_methods = ["HGB30", "RF30", "equal_average", "oof_inverse_mae", "adaptive_error_gate",
                        "multires_error_gate", "cross_window_error_gate", "cross_window_no_disagreement"]
    metrics.loc[metrics.method.isin(ablation_methods)].to_csv(args.results_dir / "feature_ablation.csv", index=False)
    pd.concat(noise_tables, ignore_index=True).to_csv(args.results_dir / "noise_robustness.csv", index=False)
    pd.concat(importance_tables, ignore_index=True).to_csv(args.results_dir / "feature_group_importance.csv", index=False)
    pd.concat(inference_tables, ignore_index=True).to_csv(args.results_dir / "inference_benchmark.csv", index=False)
    predictions_for_bootstrap = predictions.loc[:, ["subset", "method", "engine_id", "cycle", "RUL_true_capped", "RUL_pred"]].copy()
    paired_bootstrap(predictions_for_bootstrap, args).to_csv(args.results_dir / "paired_bootstrap.csv", index=False)
    metadata = {
        "project": "DARE-RUL", "phase": 7, "status": "PASS", "rul_cap": args.rul_cap,
        "seed": args.seed, "bootstrap_repeats": args.bootstrap_repeats,
        "permutation_repeats": args.permutation_repeats, "noise_repeats": args.noise_repeats,
        "official_test_targets_used": False,
        "phase6_baseline_metric_rows": int(len(base_metrics)), "combined_metric_rows": int(len(metrics)),
        "combined_prediction_rows": int(len(predictions)), "new_gate_variants": list(VARIANTS),
        "engine_balanced_gate_training": True,
        "cross_window_features_per_sensor": ["mean contrast w15-w30", "std ratio w15/w30", "delta contrast w15-w30", "current vs w30 z-score"],
        "cross_window_features_added": 84,
        "outputs": ["validation_metrics.csv", "validation_predictions.csv", "feature_ablation.csv", "noise_robustness.csv", "paired_bootstrap.csv", "feature_group_importance.csv", "inference_benchmark.csv"],
        "subsets": subset_summary,
        "limitations": ["validation results are exploratory and conditional on the reused Phase 5 split", "125-cycle cap is provisional", "local in-process inference benchmark does not prove distributed scalability", "official test labels were not loaded", "successful execution does not prove novelty or improvement"]
    }
    (args.results_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_summary(metrics, pd.concat(noise_tables, ignore_index=True), pd.read_csv(args.results_dir / "paired_bootstrap.csv"),
                  pd.concat(importance_tables, ignore_index=True), pd.concat(inference_tables, ignore_index=True),
                  ROOT / "docs" / "project" / "phase7_run_summary.md", args.seed, args.rul_cap)
    print("\nPHASE 7 EXPERIMENT PASS", flush=True)
    print(f"Metrics: {args.results_dir / 'validation_metrics.csv'}", flush=True)
    print(f"Ablation: {args.results_dir / 'feature_ablation.csv'}", flush=True)
    print(f"Noise robustness: {args.results_dir / 'noise_robustness.csv'}", flush=True)
    print(f"Bootstrap CIs: {args.results_dir / 'paired_bootstrap.csv'}", flush=True)
    print(f"Group explainability: {args.results_dir / 'feature_group_importance.csv'}", flush=True)
    print(f"Inference benchmark: {args.results_dir / 'inference_benchmark.csv'}", flush=True)
    print(f"Summary: {ROOT / 'docs' / 'project' / 'phase7_run_summary.md'}", flush=True)
    print("Official test RUL files were not loaded.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
