"""Inference parity service for the saved Phase 8 models and gates.

The implementation intentionally calls the same feature selectors, context
transformations, gates and blending helper used by the Phase 8 runner.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
EXPERTS = ("RF15", "HGB15", "RF30", "HGB30")
VARIANT_DISAGREEMENT = {"cross_window_error_gate": True, "cross_window_no_disagreement": False}


@dataclass
class Bundle:
    subset: str
    train: pd.DataFrame
    test: pd.DataFrame
    feature_columns: list[str]
    window_columns: dict[str, list[str]]
    models: dict[str, Any]
    gates: dict[str, Any]
    meta_feature_columns: list[str]
    variant: str
    cap: int


class SavedEnsembleService:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root).resolve()
        metadata_path = self.root / "results" / "phase8" / "run_metadata.json"
        predictions_path = self.root / "results" / "phase8" / "test_predictions.csv"
        if not metadata_path.is_file() or not predictions_path.is_file():
            raise FileNotFoundError("Phase 8 metadata/predictions are missing; run the Phase 8 evaluation first")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.predictions = pd.read_csv(predictions_path, encoding="utf-8-sig")
        self._bundles: dict[str, Bundle] = {}

    def _load_bundle(self, subset: str) -> Bundle:
        if subset not in SUBSETS:
            raise ValueError(f"Unknown subset: {subset}")
        if subset in self._bundles:
            return self._bundles[subset]

        # Imports are local so non-XAI dashboard pages still open if a model dependency is missing.
        from scripts.phase5.baseline_core import select_feature_columns
        from scripts.phase7.phase7_core import enhanced_context, gate_expected_errors, meta_features  # noqa: F401

        features_dir = self.root / "data" / "features" / "phase4" / subset
        train_path = features_dir / "train_features.parquet"
        test_path = features_dir / "test_features.parquet"
        if not train_path.is_file() or not test_path.is_file():
            raise FileNotFoundError(f"Phase 4 parquet features are missing for {subset}: {features_dir}")
        train = pd.read_parquet(train_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
        test = pd.read_parquet(test_path).sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)

        models_dir = self.root / "models" / "phase8" / subset
        variant = self.metadata["final_variant_by_subset"][subset]
        if variant not in VARIANT_DISAGREEMENT:
            raise ValueError(f"Unexpected frozen Phase 8 variant for {subset}: {variant}")
        models = {expert: joblib.load(models_dir / f"{expert}.joblib") for expert in EXPERTS}
        gates = {expert: joblib.load(models_dir / f"gate_{variant}_{expert}.joblib") for expert in EXPERTS}
        spec_path = models_dir / f"gate_feature_spec_{variant}.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        win15 = select_feature_columns(train, 15)
        win30 = select_feature_columns(train, 30)
        feature_columns = list(dict.fromkeys(win15 + win30))
        forbidden = {"engine_id", "cycle", "RUL", "RUL_true", "RUL_true_capped"}
        if forbidden.intersection(feature_columns):
            raise ValueError("Identifier/target columns appeared in explainable features")
        bundle = Bundle(
            subset=subset, train=train, test=test, feature_columns=feature_columns,
            window_columns={"RF15": win15, "HGB15": win15, "RF30": win30, "HGB30": win30},
            models=models, gates=gates,
            meta_feature_columns=list(spec["meta_feature_columns"]), variant=variant,
            cap=int(self.metadata["training_rul_cap"]),
        )
        self._bundles[subset] = bundle
        return bundle

    def test_engines(self, subset: str) -> list[int]:
        bundle = self._load_bundle(subset)
        return sorted(bundle.test["engine_id"].astype(int).unique().tolist())

    def target_row(self, subset: str, engine_id: int) -> pd.Series:
        bundle = self._load_bundle(subset)
        matches = bundle.test.loc[bundle.test["engine_id"].astype(int) == int(engine_id)]
        if len(matches) != 1:
            raise ValueError(f"Expected one final-cycle feature row for {subset} engine {engine_id}; found {len(matches)}")
        return matches.iloc[0]

    def predict_feature_matrix(self, subset: str, base_row: pd.Series, matrix: np.ndarray) -> np.ndarray:
        """Predict for perturbed raw feature rows while keeping ID/cycle metadata fixed."""
        from scripts.phase5.baseline_core import clipped_predictions
        from scripts.phase6.ensemble_core import adaptive_blend
        from scripts.phase7.phase7_core import enhanced_context, gate_expected_errors, meta_features

        bundle = self._load_bundle(subset)
        matrix = np.asarray(matrix, dtype=float)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.ndim != 2 or matrix.shape[1] != len(bundle.feature_columns):
            raise ValueError(f"Expected matrix shape (n, {len(bundle.feature_columns)}), got {matrix.shape}")
        if not np.isfinite(matrix).all():
            raise ValueError("SHAP perturbed feature matrix contains non-finite values")

        base = base_row.drop(labels=[c for c in ("RUL", "RUL_true", "RUL_true_capped") if c in base_row.index])
        frame = pd.DataFrame([base.to_dict()] * len(matrix)).reset_index(drop=True)
        for column_idx, column in enumerate(bundle.feature_columns):
            frame[column] = matrix[:, column_idx]

        pred_values: dict[str, np.ndarray] = {}
        for expert in EXPERTS:
            columns = bundle.window_columns[expert]
            pred_values[expert] = clipped_predictions(bundle.models[expert].predict(frame[columns]), bundle.cap)
        expert_frame = pd.DataFrame(pred_values)
        context = enhanced_context(frame, add_cross_window=True)
        meta_frame = meta_features(
            context, expert_frame,
            include_disagreement=VARIANT_DISAGREEMENT[bundle.variant],
        )
        if list(meta_frame.columns) != bundle.meta_feature_columns:
            raise ValueError("Dashboard meta-feature schema differs from the saved Phase 8 gate schema")
        expected_errors = gate_expected_errors(bundle.gates, meta_frame)
        blended, _weights = adaptive_blend(expert_frame, expected_errors, error_floor=0.5)
        return clipped_predictions(blended, bundle.cap)

    def parity_report(self, subset: str, engine_id: int, tolerance: float = 1e-4) -> dict[str, Any]:
        bundle = self._load_bundle(subset)
        row = self.target_row(subset, engine_id)
        x = row.loc[bundle.feature_columns].to_numpy(dtype=float)
        reconstructed = float(self.predict_feature_matrix(subset, row, x)[0])
        saved_rows = self.predictions.loc[
            (self.predictions["subset"] == subset)
            & (self.predictions["engine_id"].astype(int) == int(engine_id))
        ]
        if len(saved_rows) != 1:
            raise ValueError("Saved Phase 8 prediction artifact has no unique selected engine row")
        saved = float(saved_rows.iloc[0]["predicted_rul"])
        return {
            "passed": bool(np.isclose(reconstructed, saved, atol=tolerance, rtol=1e-5)),
            "saved_prediction": saved,
            "reconstructed_prediction": reconstructed,
            "absolute_difference": abs(reconstructed - saved),
            "tolerance": tolerance,
        }

    def explain_engine(self, subset: str, engine_id: int, background_size: int = 5, permutations: int = 1) -> pd.DataFrame:
        """Return end-to-end model-agnostic SHAP attributions for one final-cycle engine row."""
        try:
            import shap
        except ImportError as exc:
            raise RuntimeError("SHAP is not installed. Run pip install -r requirements-dashboard.txt") from exc

        bundle = self._load_bundle(subset)
        row = self.target_row(subset, engine_id)
        parity = self.parity_report(subset, engine_id)
        if not parity["passed"]:
            raise RuntimeError(
                "Prediction parity check failed; do not show SHAP until the saved model reconstruction matches. "
                f"Details: {parity}"
            )

        background_frame = bundle.train.loc[:, bundle.feature_columns]
        background_frame = background_frame.replace([np.inf, -np.inf], np.nan).dropna()
        if background_frame.empty:
            raise ValueError("No finite training-feature background rows available for SHAP")
        background_size = max(2, min(int(background_size), len(background_frame)))
        background = background_frame.sample(n=background_size, random_state=42).to_numpy(dtype=float)
        row_matrix = row.loc[bundle.feature_columns].to_numpy(dtype=float).reshape(1, -1)
        if not np.isfinite(row_matrix).all():
            raise ValueError("Selected engine has non-finite explainer inputs")

        predict_fn = lambda values: self.predict_feature_matrix(subset, row, np.asarray(values, dtype=float))
        explainer = shap.PermutationExplainer(predict_fn, background, seed=42)
        feature_count = len(bundle.feature_columns)
        max_evals = (2 * feature_count + 1) * max(1, min(int(permutations), 3))
        explanation = explainer(row_matrix, max_evals=max_evals)
        values = np.asarray(explanation.values, dtype=float).reshape(-1, feature_count)[0]
        feature_values = row_matrix[0]
        base_value = float(np.asarray(explanation.base_values, dtype=float).reshape(-1)[0])
        model_prediction = float(self.predict_feature_matrix(subset, row, row_matrix)[0])
        result = pd.DataFrame({
            "feature": bundle.feature_columns,
            "feature_value": feature_values,
            "shap_value_cycles": values,
            "absolute_shap_value": np.abs(values),
            "expected_value_rul_cycles": base_value,
            "model_prediction_rul_cycles": model_prediction,
        })
        return result.sort_values("absolute_shap_value", ascending=False, kind="stable").reset_index(drop=True)
