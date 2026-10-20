"""Run a single frozen evaluation on the official NASA C-MAPSS test targets.

Training target cap defaults to 125 to match Phases 5-7. The cap remains a
provisional Phase 1 protocol decision, so document this run accordingly until
approved by the team/mentor. Test RUL targets are not read until prediction-only
outputs have been written; targets are used only for scoring, never fitting or
method selection.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase5.baseline_core import (  # noqa: E402
    build_regressor,
    calculate_metrics,
    capped_target,
    clipped_predictions,
    select_feature_columns,
)
from scripts.phase6.ensemble_core import (  # noqa: E402
    EXPERTS,
    adaptive_blend,
    build_error_gate,
    engine_balanced_sample_weights,
)
from scripts.phase7.phase7_core import (  # noqa: E402
    enhanced_context,
    gate_expected_errors,
    meta_features,
)

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
# Frozen now, based on the strongest Phase 7 validation RMSE previously observed.
# Do not alter these after inspecting official test results.
FINAL_VARIANTS = {
    "FD001": "cross_window_no_disagreement",
    "FD002": "cross_window_error_gate",
    "FD003": "cross_window_error_gate",
    "FD004": "cross_window_no_disagreement",
}
VARIANT_DISAGREEMENT = {
    "cross_window_error_gate": True,
    "cross_window_no_disagreement": False,
}
EXPERT_SPECS = (("RF15", "RF", 15), ("HGB15", "HGB", 15), ("RF30", "RF", 30), ("HGB30", "HGB", 30))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", type=Path, default=ROOT / "data" / "features" / "phase4")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results" / "phase8")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "models" / "phase8")
    parser.add_argument("--subsets", nargs="+", choices=SUBSETS, default=list(SUBSETS))
    parser.add_argument("--rul-cap", type=int, default=125, help="Training target cap; 125 keeps the Phase 5-7 setting")
    parser.add_argument("--oof-folds", type=int, default=5, help="Engine-grouped folds used to train the error gates")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--protocol-approved", action="store_true", help="Record that the team/mentor has approved the target cap and metric/split protocol before test scoring")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly overwrite prior Phase 8 outputs; avoid rerunning to tune on test results")
    return parser.parse_args()


def validate_test_predictor_schema(test: pd.DataFrame, subset: str = "test") -> None:
    """Reject labels/identifiers that could leak into the model predictor table."""
    forbidden = {"RUL", "RUL_true", "RUL_true_capped"}
    leaked = forbidden.intersection(test.columns)
    if leaked:
        raise ValueError(f"{subset}: test predictor table contains target columns: {sorted(leaked)}")
    required = {"engine_id", "cycle", "setting_1", "setting_2", "setting_3"}
    missing = required - set(test.columns)
    if missing:
        raise ValueError(f"{subset}: test feature table missing required columns: {sorted(missing)}")


def validate_inputs(features_dir: Path, subset: str) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    subset_dir = features_dir / subset
    train_path = subset_dir / "train_features.parquet"
    test_path = subset_dir / "test_features.parquet"
    target_path = subset_dir / "test_targets.csv"
    for path in (train_path, test_path, target_path):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run .\\scripts\\phase4\\run_phase4.ps1 first and verify Phase 4 completed."
            )

    train = pd.read_parquet(train_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    test = pd.read_parquet(test_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)

    if train.empty or test.empty:
        raise ValueError(f"{subset}: training or test feature table is empty")
    if not {"engine_id", "cycle", "RUL"}.issubset(train.columns):
        raise ValueError(f"{subset}: training features must contain engine_id, cycle and RUL")
    validate_test_predictor_schema(test, subset)
    for name, frame in (("train", train), ("test", test)):
        if frame.duplicated(["engine_id", "cycle"]).any():
            raise ValueError(f"{subset}: duplicate engine-cycle keys in {name} features")
        if frame[["engine_id", "cycle"]].isna().any().any():
            raise ValueError(f"{subset}: missing engine-cycle identifiers in {name} features")

    # C-MAPSS reuses local engine IDs in train and test (for example both can
    # contain engine_id=1); they are separate partitions, so cross-file ID overlap
    # is normal and must not be treated as leakage.
    if test.duplicated(["engine_id"]).any():
        # Phase 4 test_features.parquet must have one final row per test engine.
        raise ValueError(f"{subset}: test_features.parquet should contain one final row per engine")

    # Validate all feature selectors now, before expensive model fitting.
    for _, _, window in EXPERT_SPECS:
        cols = select_feature_columns(train, window)
        missing = set(cols) - set(test.columns)
        if missing:
            raise ValueError(f"{subset}: test features miss columns required for window {window}: {sorted(missing)[:8]}")
        forbidden = {"engine_id", "cycle", "RUL", "RUL_true_capped"}
        if forbidden.intersection(cols):
            raise AssertionError(f"{subset}: identifier/target entered model feature list")
    return train, test, target_path


def fit_oof_experts(train: pd.DataFrame, subset: str, rul_cap: int, folds: int, seed: int) -> tuple[pd.DataFrame, dict[str, np.ndarray], pd.DataFrame]:
    """Generate OOF expert predictions by holding out complete engines."""
    engine_count = train.engine_id.nunique()
    if folds < 2 or folds > engine_count:
        raise ValueError(f"{subset}: oof-folds must be between 2 and engine count ({engine_count})")
    y = capped_target(train, rul_cap)
    groups = train.engine_id.to_numpy(dtype=int)
    oof_prediction: dict[str, np.ndarray] = {name: np.full(len(train), np.nan, dtype=float) for name, _, _ in EXPERT_SPECS}
    fold_rows: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=folds)

    for fold_index, (fit_idx, hold_idx) in enumerate(splitter.split(train, y, groups=groups), start=1):
        fit_engines = set(groups[fit_idx].tolist())
        hold_engines = set(groups[hold_idx].tolist())
        if fit_engines.intersection(hold_engines):
            raise AssertionError("OOF split leaked an engine between fit and holdout")
        for expert, model_kind, window in EXPERT_SPECS:
            columns = select_feature_columns(train, window)
            model = build_regressor(model_kind, seed=seed)
            model.fit(train.iloc[fit_idx][columns], y[fit_idx])
            predictions = clipped_predictions(model.predict(train.iloc[hold_idx][columns]), rul_cap)
            oof_prediction[expert][hold_idx] = predictions
            del model
            gc.collect()
        fold_rows.append({
            "subset": subset,
            "fold": fold_index,
            "fit_engine_count": len(fit_engines),
            "held_out_engine_count": len(hold_engines),
            "held_out_row_count": len(hold_idx),
            "engine_overlap": False,
        })
        print(f"  OOF fold {fold_index}/{folds}: fit engines={len(fit_engines)}, held-out engines={len(hold_engines)}", flush=True)

    oof = pd.DataFrame(oof_prediction)
    if oof.isna().any().any() or not np.isfinite(oof.to_numpy(dtype=float)).all():
        raise ValueError(f"{subset}: OOF expert predictions contain missing or non-finite values")
    return oof, {"RUL_true_capped": y}, pd.DataFrame(fold_rows)


def fit_final_experts(train: pd.DataFrame, subset: str, rul_cap: int, seed: int, model_dir: Path) -> dict[str, Any]:
    """Fit each final expert using all labeled training engines."""
    y = capped_target(train, rul_cap)
    fitted: dict[str, Any] = {}
    feature_spec: dict[str, list[str]] = {}
    model_dir.mkdir(parents=True, exist_ok=True)
    for expert, model_kind, window in EXPERT_SPECS:
        columns = select_feature_columns(train, window)
        model = build_regressor(model_kind, seed=seed)
        model.fit(train[columns], y)
        joblib.dump(model, model_dir / f"{expert}.joblib", compress=3)
        fitted[expert] = model
        feature_spec[expert] = columns
        print(f"  Final expert fitted: {expert} on all {train.engine_id.nunique()} train engines", flush=True)
    return {"models": fitted, "feature_columns": feature_spec, "target": y}


def predict_test_experts(test: pd.DataFrame, fitted: dict[str, Any], rul_cap: int) -> pd.DataFrame:
    output = test[["engine_id", "cycle"]].rename(columns={"cycle": "final_cycle"}).copy()
    for expert, _, _ in EXPERT_SPECS:
        columns = fitted["feature_columns"][expert]
        output[f"pred_{expert}"] = clipped_predictions(fitted["models"][expert].predict(test[columns]), rul_cap)
    return output


def train_error_gates(
    train: pd.DataFrame,
    oof_experts: pd.DataFrame,
    y_capped: np.ndarray,
    subset: str,
    variant: str,
    seed: int,
    model_dir: Path,
) -> tuple[dict[str, Any], pd.DataFrame, list[str]]:
    """Fit expected-error gates exclusively from training-engine OOF predictions."""
    include_disagreement = VARIANT_DISAGREEMENT[variant]
    context = enhanced_context(train, add_cross_window=True)
    pred_frame = oof_experts.loc[:, list(EXPERTS)].copy()
    X_meta = meta_features(context, pred_frame, include_disagreement=include_disagreement)
    weights = engine_balanced_sample_weights(train.engine_id.astype(int).tolist())
    gates: dict[str, Any] = {}
    model_dir.mkdir(parents=True, exist_ok=True)
    for expert in EXPERTS:
        abs_error_target = np.abs(pred_frame[expert].to_numpy(dtype=float) - y_capped)
        gate = build_error_gate(seed=seed)
        gate.fit(X_meta.to_numpy(dtype=np.float32), abs_error_target, sample_weight=weights)
        gates[expert] = gate
        joblib.dump(gate, model_dir / f"gate_{variant}_{expert}.joblib", compress=3)
        del gate
        gc.collect()
    (model_dir / f"gate_feature_spec_{variant}.json").write_text(
        json.dumps({
            "subset": subset,
            "variant": variant,
            "include_cross_window_features": True,
            "include_explicit_disagreement_features": include_disagreement,
            "context_columns": list(context.columns),
            "meta_feature_columns": list(X_meta.columns),
            "meta_feature_count": len(X_meta.columns),
            "oof_engine_count": int(train.engine_id.nunique()),
            "oof_row_count": int(len(train)),
            "oof_folds": "engine-grouped; see results/phase8/oof_fold_audit.csv",
            "test_targets_used": False,
        }, indent=2), encoding="utf-8"
    )
    return gates, context, list(X_meta.columns)


def run_subset(subset: str, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print(f"\n=== Phase 8 final evaluation: {subset} ===", flush=True)
    train, test, target_path = validate_inputs(args.features_dir.resolve(), subset)
    print(f"Train rows={len(train):,}; train engines={train.engine_id.nunique()}; test engines={test.engine_id.nunique()}", flush=True)
    variant = FINAL_VARIANTS[subset]
    oof_frame, y_bundle, fold_audit = fit_oof_experts(train, subset, args.rul_cap, args.oof_folds, args.seed)
    y_capped = y_bundle["RUL_true_capped"]
    model_dir = args.models_dir / subset
    fitted = fit_final_experts(train, subset, args.rul_cap, args.seed, model_dir)
    gates, _, _ = train_error_gates(train, oof_frame, y_capped, subset, variant, args.seed, model_dir)

    expert_predictions = predict_test_experts(test, fitted, args.rul_cap)
    test_context = enhanced_context(test, add_cross_window=True)
    pred_frame = expert_predictions[[f"pred_{name}" for name in EXPERTS]].copy()
    pred_frame.columns = list(EXPERTS)
    meta_X = meta_features(test_context, pred_frame, include_disagreement=VARIANT_DISAGREEMENT[variant])
    # Guard against train/test feature-schema drift.
    spec = json.loads((model_dir / f"gate_feature_spec_{variant}.json").read_text(encoding="utf-8"))
    if list(meta_X.columns) != spec["meta_feature_columns"]:
        raise ValueError(f"{subset}: test gate-feature schema differs from OOF gate-training schema")
    expected_errors = gate_expected_errors(gates, meta_X)
    blended, weights = adaptive_blend(pred_frame, expected_errors, error_floor=0.5)
    predicted_rul = clipped_predictions(blended, args.rul_cap)

    output = expert_predictions.copy()
    output["subset"] = subset
    output["selected_method"] = variant
    output["training_rul_cap"] = args.rul_cap
    output["predicted_rul"] = predicted_rul
    for expert in EXPERTS:
        output[f"expected_error_{expert}"] = expected_errors[expert].to_numpy(dtype=float)
    output = pd.concat([output.reset_index(drop=True), weights.reset_index(drop=True)], axis=1)
    output = output[[
        "subset", "engine_id", "final_cycle", "selected_method", "training_rul_cap", "predicted_rul",
        *[f"pred_{e}" for e in EXPERTS], *[f"expected_error_{e}" for e in EXPERTS], *[f"weight_{e}" for e in EXPERTS],
    ]].sort_values("engine_id", kind="stable").reset_index(drop=True)
    if len(output) != test.engine_id.nunique() or output.engine_id.duplicated().any():
        raise ValueError(f"{subset}: expected exactly one prediction per test engine")
    if not np.isfinite(output["predicted_rul"].to_numpy(dtype=float)).all():
        raise ValueError(f"{subset}: final predictions contain non-finite values")
    print(f"  Predicted {len(output)} test engines using frozen method {variant}", flush=True)
    return output, fold_audit, pd.DataFrame({"subset": [subset], "test_engine_count": [len(output)], "target_path_for_later_scoring": [str(target_path)]})


def main() -> int:
    args = parse_args()
    if args.rul_cap < 1:
        raise SystemExit("ERROR: --rul-cap must be a positive integer")
    if args.oof_folds < 2:
        raise SystemExit("ERROR: --oof-folds must be at least 2")
    if args.results_dir.exists() and not args.overwrite:
        existing = [args.results_dir / n for n in ("test_predictions.csv", "test_scored_predictions.csv", "final_test_metrics.csv") if (args.results_dir / n).exists()]
        if existing:
            raise SystemExit(
                "ERROR: Phase 8 final-test outputs already exist. Do not rerun to tune using test results. "
                "For recovery from a technical/incomplete run only, inspect outputs and explicitly pass --overwrite."
            )
    if not args.features_dir.exists():
        raise SystemExit(f"ERROR: feature directory not found: {args.features_dir}. Run Phase 4 first.")

    start = time.perf_counter()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    # Avoid appending stale fold-audit rows on a deliberate recovery run.
    stale_outputs = [
        args.results_dir / name for name in (
            "test_predictions.csv", "test_scored_predictions.csv", "final_test_metrics.csv",
            "final_test_summary.md", "run_metadata.json", "oof_fold_audit.csv"
        ) if (args.results_dir / name).exists()
    ]
    if args.overwrite:
        for stale in stale_outputs:
            stale.unlink()

    all_predictions = []
    all_fold_audits = []
    for subset in args.subsets:
        prediction, audit, _ = run_subset(subset, args)
        all_predictions.append(prediction)
        all_fold_audits.append(audit)
        gc.collect()

    predictions = pd.concat(all_predictions, ignore_index=True)
    predictions_path = args.results_dir / "test_predictions.csv"
    predictions.to_csv(predictions_path, index=False)
    print(f"\nPREDICTIONS SAVED BEFORE OFFICIAL LABELS ARE OPENED: {predictions_path}", flush=True)

    # Only now read official targets; they're for scoring only and never enter fitting/selection.
    scored_chunks = []
    metrics_rows = []
    for subset in args.subsets:
        target_path = args.features_dir.resolve() / subset / "test_targets.csv"
        targets = pd.read_csv(target_path)
        if not {"engine_id", "RUL"}.issubset(targets.columns):
            raise ValueError(f"{target_path}: expected columns engine_id,RUL")
        if targets.engine_id.duplicated().any() or targets.RUL.isna().any():
            raise ValueError(f"{target_path}: duplicate engines or missing RUL target")
        subset_pred = predictions.loc[predictions.subset == subset].copy().sort_values("engine_id", kind="stable")
        targets["engine_id"] = targets.engine_id.astype(int)
        targets["RUL"] = pd.to_numeric(targets.RUL, errors="raise").astype(float)
        if not np.isfinite(targets.RUL.to_numpy(dtype=float)).all() or (targets.RUL < 0).any():
            raise ValueError(f"{target_path}: official RUL targets must be finite and non-negative")
        joined = subset_pred.merge(targets.rename(columns={"RUL": "RUL_true"}), on="engine_id", how="left", validate="one_to_one")
        if joined.RUL_true.isna().any() or len(joined) != len(targets):
            raise ValueError(f"{subset}: test predictions and official target engine IDs do not align")
        joined["error_pred_minus_true"] = joined.predicted_rul - joined.RUL_true
        joined["absolute_error"] = joined.error_pred_minus_true.abs()
        scored_chunks.append(joined)
        metrics = calculate_metrics(joined.RUL_true.to_numpy(dtype=float), joined.predicted_rul.to_numpy(dtype=float))
        metrics_rows.append({
            "subset": subset,
            "selected_method": FINAL_VARIANTS[subset],
            "test_engines": int(len(joined)),
            "training_rul_cap": int(args.rul_cap),
            "official_test_targets_capped": False,
            **metrics,
        })
        print(f"  {subset}: test engines={len(joined)}, RMSE={metrics['rmse']:.4f}, MAE={metrics['mae']:.4f}, NASA score sum={metrics['nasa_score_sum']:.4f}", flush=True)

    scored = pd.concat(scored_chunks, ignore_index=True)
    metrics_frame = pd.DataFrame(metrics_rows)
    scored.to_csv(args.results_dir / "test_scored_predictions.csv", index=False)
    metrics_frame.to_csv(args.results_dir / "final_test_metrics.csv", index=False)
    audit = pd.concat(all_fold_audits, ignore_index=True)
    audit.to_csv(args.results_dir / "oof_fold_audit.csv", index=False)

    metadata = {
        "phase": 8,
        "status": "PASS",
        "subsets": list(args.subsets),
        "seed": int(args.seed),
        "oof_folds": int(args.oof_folds),
        "training_rul_cap": int(args.rul_cap),
        "protocol_approved_before_test_scoring": bool(args.protocol_approved),
        "rul_cap_is_still_provisional": not bool(args.protocol_approved),
        "final_variant_by_subset": {s: FINAL_VARIANTS[s] for s in args.subsets},
        "variant_selection_basis": "Frozen from Phase 7 validation RMSE before official test labels were read",
        "final_experts_fit_on_all_train_engines": True,
        "gate_training_basis": "engine-grouped OOF predictions over all labeled training engines only",
        "official_test_targets_used_for_training_or_selection": False,
        "official_test_targets_read_after_prediction_csv_written_for_scoring_only": True,
        "test_targets_scored_uncapped": True,
        "prediction_clip_range": [0, int(args.rul_cap)],
        "elapsed_seconds_including_official_scoring": round(time.perf_counter() - start, 3),
        "limitations": [
            "The training RUL cap of 125 remains provisional until Phase 1 protocol review/approval.",
            "The official test cohort is a final evaluation cohort and must not be used for repeated model tuning.",
            "Phase 7 validation cohort was reused during prior comparisons; reported Phase 7 method choices are frozen before this test scoring.",
            "Maintenance risk tiers are illustrative project-demo rules, not approved aircraft maintenance instructions.",
        ],
    }
    (args.results_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_summary(args.results_dir / "final_test_summary.md", metrics_frame, metadata)
    print(f"\nPHASE 8 TEST EVALUATION PASS")
    print(f"Predictions (no labels): {predictions_path}")
    print(f"Scored predictions: {args.results_dir / 'test_scored_predictions.csv'}")
    print(f"Metrics: {args.results_dir / 'final_test_metrics.csv'}")
    print(f"Summary: {args.results_dir / 'final_test_summary.md'}")
    print("Reminder: do not select/tune the model after reviewing these official test scores.")
    return 0


def write_summary(path: Path, metrics: pd.DataFrame, metadata: dict[str, Any]) -> None:
    lines = [
        "# Phase 8 Official C-MAPSS Test Evaluation",
        "",
        f"- **Status:** {metadata['status']}",
        f"- **Training RUL cap:** {metadata['training_rul_cap']} cycles " + ("(provisional; Phase 1 approval not recorded)" if metadata["rul_cap_is_still_provisional"] else "(protocol marked approved before scoring)"),
        f"- **OOF gate folds:** {metadata['oof_folds']} engine-grouped folds over all available labeled training engines",
        "- **Official test targets:** read only after test predictions were written; used for scoring only, not fitting or method selection",
        "- **Official test labels:** evaluated without capping target RUL; model predictions are clipped to the configured training cap for consistency with earlier phases",
        "",
        "## Results",
        "",
        "| Subset | Frozen method | Test engines | RMSE | MAE | NASA score sum | NASA score mean |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in metrics.to_dict("records"):
        lines.append(
            f"| {row['subset']} | {row['selected_method']} | {int(row['test_engines'])} | "
            f"{float(row['rmse']):.4f} | {float(row['mae']):.4f} | "
            f"{float(row['nasa_score_sum']):.4f} | {float(row['nasa_score_mean']):.6f} |"
        )
    lines += [
        "",
        "## Frozen method selection",
        "",
        "| Subset | Method chosen before official target scoring |",
        "|---|---|",
    ]
    for subset, variant in metadata["final_variant_by_subset"].items():
        lines.append(f"| {subset} | `{variant}` |")
    lines += [
        "",
        "## Interpretation and limits",
        "",
        "- These scores are the official test-cohort results for this frozen run, not evidence of universal superiority or real-aircraft readiness.",
        "- Do not change features, methods, seed, cap or thresholds because of these test scores and then report the same cohort as an untouched test set.",
        "- The model was trained with capped training labels. The official test targets remain uncapped for scoring, so targets above the cap can contribute larger errors.",
        "- If the target cap/protocol was not approved before this run, label these metrics exploratory and resolve Phase 1 before making a definitive claim. Do not run another variant based on the observed scores.",
        "- This is a benchmark evaluation, not validated real-world maintenance guidance.",
        "",
        "Artifacts under `results/phase8/` and `models/phase8/` are local experiment outputs; keep large artifacts out of Git.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
