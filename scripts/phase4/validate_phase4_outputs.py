"""Read back and validate the generated DARE-RUL Phase 4 feature files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
EXPECTED_BASE_FILES = (
    "train_features.parquet",
    "test_trajectory_features.parquet",
    "test_features.parquet",
    "test_targets.csv",
    "metadata.json",
)


def fail(message: str) -> None:
    raise ValueError(message)


def check_numeric_finite(frame: pd.DataFrame, label: str) -> None:
    numeric = frame.select_dtypes(include=[np.number])
    if numeric.shape[1] != frame.shape[1]:
        non_numeric = [c for c in frame.columns if c not in numeric.columns]
        fail(f"{label}: unexpected non-numeric columns: {non_numeric}")
    if frame.isna().any().any():
        fail(f"{label}: missing/null values found")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        fail(f"{label}: NaN or infinity found")


def validate_pair_keys(frame: pd.DataFrame, label: str) -> None:
    required = {"engine_id", "cycle"}
    if not required.issubset(frame.columns):
        fail(f"{label}: missing engine_id/cycle columns")
    if frame.duplicated(["engine_id", "cycle"]).any():
        fail(f"{label}: duplicate (engine_id, cycle) keys found")
    ordered = frame.sort_values(["engine_id", "cycle"], kind="stable")
    if not ordered[["engine_id", "cycle"]].reset_index(drop=True).equals(
        frame[["engine_id", "cycle"]].reset_index(drop=True)
    ):
        fail(f"{label}: rows are not ordered by engine_id then cycle")
    steps = frame.groupby("engine_id", sort=False)["cycle"].diff().dropna()
    if (steps <= 0).any():
        fail(f"{label}: cycles do not strictly increase within an engine")


def validate_subset(root: Path, subset: str, expected: dict) -> list[str]:
    folder = root / subset
    absent = [name for name in EXPECTED_BASE_FILES if not (folder / name).is_file()]
    if absent:
        fail(f"{subset}: missing required output file(s): {absent}")

    train = pd.read_parquet(folder / "train_features.parquet")
    trajectory = pd.read_parquet(folder / "test_trajectory_features.parquet")
    final = pd.read_parquet(folder / "test_features.parquet")
    targets = pd.read_csv(folder / "test_targets.csv")
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))

    for label, frame in (("train", train), ("test trajectory", trajectory), ("test final", final)):
        check_numeric_finite(frame, f"{subset} {label}")
        validate_pair_keys(frame, f"{subset} {label}")

    if "RUL" not in train.columns:
        fail(f"{subset}: training table has no RUL target")
    if "RUL" in trajectory.columns or "RUL" in final.columns:
        fail(f"{subset}: test feature Parquet unexpectedly contains RUL")

    train_features = [c for c in train.columns if c != "RUL"]
    if trajectory.columns.tolist() != train_features or final.columns.tolist() != train_features:
        fail(f"{subset}: train/test feature columns or their order do not match")
    if len(train_features) != int(expected["feature_column_count_including_engine_cycle_settings_current_sensors_and_rolling"]):
        fail(f"{subset}: feature-column count disagrees with build summary")
    if len(train) != int(expected["train_rows"]):
        fail(f"{subset}: train row count disagrees with build summary")
    if train["engine_id"].nunique() != int(expected["train_engines"]):
        fail(f"{subset}: train engine count disagrees with build summary")
    if len(trajectory) != int(expected["test_trajectory_rows"]):
        fail(f"{subset}: test trajectory row count disagrees with build summary")
    if len(final) != int(expected["test_final_rows"]):
        fail(f"{subset}: final test row count disagrees with build summary")
    if len(targets) != int(expected["test_target_count"]):
        fail(f"{subset}: target count disagrees with build summary")

    if targets.columns.tolist() != ["engine_id", "RUL"]:
        fail(f"{subset}: test_targets.csv must contain exactly engine_id,RUL")
    if targets.isna().any().any() or not np.isfinite(targets[["engine_id", "RUL"]].to_numpy(dtype=float)).all():
        fail(f"{subset}: test targets contain missing/non-finite values")
    if (targets["RUL"] < 0).any():
        fail(f"{subset}: negative test RUL target found")
    if targets["engine_id"].duplicated().any():
        fail(f"{subset}: duplicate engine_id in test targets")
    target_ids = targets["engine_id"].astype(int).tolist()
    final_ids = final["engine_id"].astype(int).tolist()
    if target_ids != final_ids:
        fail(f"{subset}: test target engine order/IDs do not match final test feature rows")

    # The final feature row must equal the last available cycle in each test trajectory.
    expected_final = trajectory.groupby("engine_id", sort=False).tail(1).reset_index(drop=True)
    pd.testing.assert_frame_equal(final.reset_index(drop=True), expected_final, check_dtype=False, check_exact=False, rtol=1e-10, atol=1e-10)

    # Current run is uncapped: the training label should equal each engine's last cycle minus the row's cycle.
    rul_cap = metadata.get("rul_cap")
    expected_rul = train.groupby("engine_id", sort=False)["cycle"].transform("max") - train["cycle"]
    if rul_cap is not None:
        expected_rul = expected_rul.clip(upper=int(rul_cap))
    if not np.array_equal(train["RUL"].astype(int).to_numpy(), expected_rul.astype(int).to_numpy()):
        fail(f"{subset}: training RUL labels do not match documented cap/remaining-cycle calculation")

    if metadata.get("subset") != subset:
        fail(f"{subset}: metadata subset name mismatch")
    if metadata.get("windows") != [15, 30]:
        fail(f"{subset}: metadata does not list expected [15, 30] windows")

    return [
        f"{subset}: PASS — train {len(train):,} rows; trajectory {len(trajectory):,} rows; "
        f"final test {len(final)} rows; targets {len(targets)}; {len(train_features)} matching features; labels/keys checked"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/features/phase4"))
    args = parser.parse_args()
    root = args.output_dir.resolve()
    manifest_path = root / "phase4_build_summary.json"
    if not manifest_path.is_file():
        print(f"FAIL: summary not found: {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS" or manifest.get("windows") != [15, 30]:
        print("FAIL: build summary status/windows are not the expected Phase 4 run", file=sys.stderr)
        return 1
    expected_by_subset = {row.get("subset"): row for row in manifest.get("subsets", [])}
    try:
        if set(expected_by_subset) != set(SUBSETS):
            fail(f"summary must include exactly {SUBSETS}, got {tuple(expected_by_subset)}")
        messages = []
        for subset in SUBSETS:
            messages.extend(validate_subset(root, subset, expected_by_subset[subset]))
        print("\n".join(messages))
        print("PHASE 4 READ-BACK QUALITY CHECK: PASS")
        print("Note: this validates data integrity and label separation, not predictive accuracy or research novelty.")
        return 0
    except Exception as exc:  # print a clear diagnostic for a research runbook
        print(f"PHASE 4 READ-BACK QUALITY CHECK: FAIL\n{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
