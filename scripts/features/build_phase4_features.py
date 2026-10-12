"""Build leakage-aware, multi-resolution temporal features for NASA C-MAPSS.

Training rows use only the current and preceding cycles from the same engine.
Test trajectory features contain no RUL labels. Final test rows are stored separately
from their official RUL targets so targets cannot accidentally enter feature creation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_COLUMNS = ["engine_id", "cycle", "setting_1", "setting_2", "setting_3"]
SENSOR_COLUMNS = [f"sensor_{i}" for i in range(1, 22)]
ALL_COLUMNS = BASE_COLUMNS + SENSOR_COLUMNS


def validate_cycles(frame: pd.DataFrame, source: str = "input") -> pd.DataFrame:
    """Validate and sort a C-MAPSS table; fail early on malformed or duplicate rows."""
    if len(frame.columns) != len(ALL_COLUMNS):
        raise ValueError(f"{source}: expected 26 columns, got {len(frame.columns)}")
    frame = frame.copy()
    frame.columns = ALL_COLUMNS
    if frame.empty:
        raise ValueError(f"{source}: file contains no rows")
    if frame.isna().any().any():
        raise ValueError(f"{source}: missing values found in raw data")
    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{source}: non-finite values found in raw data")
    frame["engine_id"] = frame["engine_id"].astype(int)
    frame["cycle"] = frame["cycle"].astype(int)
    if (frame["engine_id"] < 1).any() or (frame["cycle"] < 1).any():
        raise ValueError(f"{source}: engine IDs and cycles must be positive")
    if frame.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{source}: duplicate (engine_id, cycle) pair found")
    frame = frame.sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    increments = frame.groupby("engine_id", sort=False)["cycle"].diff()
    if (increments.dropna() <= 0).any():
        raise ValueError(f"{source}: cycles must strictly increase within each engine")
    return frame


def read_cmapss(path: Path) -> pd.DataFrame:
    """Read a whitespace-delimited NASA C-MAPSS file (no header)."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    raw = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
    return validate_cycles(raw, str(path))


def add_temporal_features(frame: pd.DataFrame, windows: Iterable[int] = (15, 30)) -> pd.DataFrame:
    """Add trailing-window mean/std/delta, grouped by engine to prevent bleed-over."""
    windows = tuple(dict.fromkeys(int(w) for w in windows))
    if not windows or any(w < 2 for w in windows):
        raise ValueError("Windows must be unique integers >= 2 (for example 15 30)")
    working = frame.copy().sort_values(["engine_id", "cycle"], kind="stable").reset_index(drop=True)
    if working.duplicated(["engine_id", "cycle"]).any():
        raise ValueError("Duplicate (engine_id, cycle) pair found before feature generation")

    groups = working.groupby("engine_id", sort=False)
    generated: dict[str, pd.Series] = {}
    for sensor in SENSOR_COLUMNS:
        grouped_sensor = groups[sensor]
        first_value = grouped_sensor.transform("first")
        for window in windows:
            prefix = f"{sensor}_w{window}"
            generated[f"{prefix}_mean"] = grouped_sensor.transform(
                lambda s, w=window: s.rolling(window=w, min_periods=1).mean()
            )
            generated[f"{prefix}_std"] = grouped_sensor.transform(
                lambda s, w=window: s.rolling(window=w, min_periods=1).std(ddof=0)
            ).fillna(0.0)
            prior = grouped_sensor.shift(window - 1)
            generated[f"{prefix}_delta"] = working[sensor] - prior.fillna(first_value)
    features = pd.concat([working, pd.DataFrame(generated, index=working.index)], axis=1)
    if not np.isfinite(features.drop(columns=[]).select_dtypes(include=[np.number]).to_numpy(dtype=float)).all():
        raise ValueError("Generated temporal features contain NaN or infinite values")
    return features


def make_train_features(raw_train: pd.DataFrame, windows: Iterable[int] = (15, 30), rul_cap: int | None = None) -> pd.DataFrame:
    """Build features for all train cycles and attach cycle-to-failure RUL targets."""
    raw_train = validate_cycles(raw_train, "training data")
    features = add_temporal_features(raw_train, windows)
    max_cycle = features.groupby("engine_id")["cycle"].transform("max")
    rul = (max_cycle - features["cycle"]).astype(int)
    if rul_cap is not None:
        if rul_cap < 1:
            raise ValueError("RUL cap must be a positive integer")
        rul = rul.clip(upper=rul_cap)
    features["RUL"] = rul
    return features


def make_test_features(raw_test: pd.DataFrame, windows: Iterable[int] = (15, 30)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return all observed test-cycle features plus the last observed row per engine."""
    raw_test = validate_cycles(raw_test, "test data")
    trajectory = add_temporal_features(raw_test, windows)
    final_rows = trajectory.groupby("engine_id", sort=False).tail(1).reset_index(drop=True)
    return trajectory, final_rows


def read_rul_targets(path: Path, test_engine_ids: list[int]) -> pd.DataFrame:
    """Pair official test RUL labels with sorted test engine IDs; labels stay separate."""
    if not path.exists():
        raise FileNotFoundError(f"Official test RUL file not found: {path}")
    values = np.loadtxt(path, dtype=float, ndmin=1)
    if values.ndim != 1 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"{path}: RUL targets must be finite non-negative numbers")
    if len(values) != len(test_engine_ids):
        raise ValueError(
            f"{path}: has {len(values)} targets but test file has {len(test_engine_ids)} engines"
        )
    return pd.DataFrame({"engine_id": test_engine_ids, "RUL": values.astype(int)})


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
    except ImportError as exc:
        raise RuntimeError("Parquet support is missing. In the project .venv run: python -m pip install pyarrow") from exc


def build_subset(data_dir: Path, output_dir: Path, subset: str, windows: tuple[int, ...], rul_cap: int | None) -> dict:
    train_raw = read_cmapss(data_dir / f"train_{subset}.txt")
    test_raw = read_cmapss(data_dir / f"test_{subset}.txt")
    target_path = data_dir / f"RUL_{subset}.txt"

    train_out = make_train_features(train_raw, windows, rul_cap)
    test_trajectory, test_final = make_test_features(test_raw, windows)
    target_ids = sorted(test_raw["engine_id"].unique().tolist())
    targets = read_rul_targets(target_path, target_ids)

    subset_dir = output_dir / subset
    write_parquet(train_out, subset_dir / "train_features.parquet")
    write_parquet(test_trajectory, subset_dir / "test_trajectory_features.parquet")
    write_parquet(test_final, subset_dir / "test_features.parquet")
    targets.to_csv(subset_dir / "test_targets.csv", index=False)

    feature_columns = [c for c in train_out.columns if c != "RUL"]
    metadata = {
        "subset": subset,
        "windows": list(windows),
        "rul_cap": rul_cap,
        "rul_cap_status": "uncapped_pending_protocol_decision" if rul_cap is None else "explicitly_configured",
        "train_engines": int(train_raw.engine_id.nunique()),
        "train_rows": int(len(train_out)),
        "test_engines": int(test_raw.engine_id.nunique()),
        "test_trajectory_rows": int(len(test_trajectory)),
        "test_final_rows": int(len(test_final)),
        "feature_column_count_including_engine_cycle_settings_current_sensors_and_rolling": len(feature_columns),
        "train_rul_min": int(train_out.RUL.min()),
        "train_rul_max": int(train_out.RUL.max()),
        "test_target_count": int(len(targets)),
        "test_target_range": [int(targets.RUL.min()), int(targets.RUL.max())],
        "files": ["train_features.parquet", "test_trajectory_features.parquet", "test_features.parquet", "test_targets.csv"],
        "safety_notes": [
            "Rolling windows use only each engine's current and preceding observed cycles.",
            "Features are computed separately per engine; windows never cross engine boundaries.",
            "Official test RUL targets are saved separately and are not used to build features.",
            "Engine ID is retained for joins/audits and must not be used as a predictive model input.",
            "Uncapped train RUL is the default while the Phase 1 target-cap decision remains open."
        ],
    }
    (subset_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/CMAPSSData"), help="Folder containing NASA C-MAPSS text files")
    parser.add_argument("--output-dir", type=Path, default=Path("data/features/phase4"), help="Local output folder (kept out of Git by project ignore rules)")
    parser.add_argument("--subsets", nargs="+", choices=["FD001", "FD002", "FD003", "FD004"], default=["FD001", "FD002", "FD003", "FD004"])
    parser.add_argument("--windows", nargs="+", type=int, default=[15, 30], help="Trailing cycle windows; defaults to 15 and 30")
    parser.add_argument("--rul-cap", type=int, default=None, help="Optional positive train RUL cap. Leave unset until Phase 1 protocol is approved.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    windows = tuple(dict.fromkeys(args.windows))
    if not windows or any(w < 2 for w in windows):
        raise SystemExit("ERROR: every window must be an integer >= 2")
    if args.rul_cap is not None and args.rul_cap < 1:
        raise SystemExit("ERROR: --rul-cap must be positive")
    print(f"Input data : {data_dir}")
    print(f"Output     : {output_dir}")
    print(f"Windows    : {windows}")
    print(f"RUL cap    : {args.rul_cap if args.rul_cap is not None else 'UNCAPPED (protocol decision still open)'}")
    summaries = []
    for subset in args.subsets:
        print(f"\n[{subset}] reading, validating and building temporal features...")
        summary = build_subset(data_dir, output_dir, subset, windows, args.rul_cap)
        summaries.append(summary)
        print(f"  PASS: train rows={summary['train_rows']:,}; test trajectory rows={summary['test_trajectory_rows']:,}; test final rows={summary['test_final_rows']}; features={summary['feature_column_count_including_engine_cycle_settings_current_sensors_and_rolling']}")
    manifest = {
        "project": "DARE-RUL",
        "phase": 4,
        "status": "PASS",
        "windows": list(windows),
        "rul_cap": args.rul_cap,
        "subsets": summaries,
        "note": "PASS means the feature-generation job and its validations completed; it does not establish predictive accuracy or prove novelty.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase4_build_summary.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nPHASE 4 FEATURE BUILD PASS. Summary: {output_dir / 'phase4_build_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
