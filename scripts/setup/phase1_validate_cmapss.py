"""Structural validation for NASA C-MAPSS FD001-FD004.

Expected location: <project>/data/CMAPSSData
This script never modifies the original dataset files.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "CMAPSSData"
RESULTS_DIR = PROJECT_ROOT / "results" / "phase1"
TEXT_REPORT = RESULTS_DIR / "cmapss_validation.txt"
JSON_REPORT = RESULTS_DIR / "cmapss_validation.json"
HASH_REPORT = RESULTS_DIR / "raw_data_sha256.csv"
DATASETS = ("FD001", "FD002", "FD003", "FD004")
EXPECTED_SENSOR_COLUMNS = 26


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sensor_file(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    frame = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
    if frame.shape[1] != EXPECTED_SENSOR_COLUMNS:
        raise ValueError(
            f"{path.name}: expected {EXPECTED_SENSOR_COLUMNS} columns, "
            f"found {frame.shape[1]}. Check that this is the original C-MAPSS file."
        )
    frame = frame.apply(pd.to_numeric, errors="raise")
    if frame.isna().any().any():
        raise ValueError(f"{path.name}: contains missing values")
    # Reject infinities as well as NaNs.
    if not all(math.isfinite(float(value)) for value in frame.to_numpy().ravel()):
        raise ValueError(f"{path.name}: contains infinite/non-finite values")
    if (frame[0] <= 0).any():
        raise ValueError(f"{path.name}: engine IDs must be positive")
    if (frame[1] <= 0).any():
        raise ValueError(f"{path.name}: cycle numbers must be positive")
    if frame.duplicated(subset=[0, 1]).any():
        raise ValueError(f"{path.name}: duplicate engine-cycle pairs found")
    for engine_id, group in frame.groupby(0, sort=False):
        cycles = group[1]
        if not cycles.is_monotonic_increasing:
            raise ValueError(
                f"{path.name}: cycle sequence is not increasing for engine {engine_id}"
            )
        if cycles.duplicated().any():
            raise ValueError(f"{path.name}: duplicate cycle for engine {engine_id}")
    return frame


def load_rul_file(path: Path) -> pd.Series:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    table = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
    if table.shape[1] != 1:
        raise ValueError(f"{path.name}: expected exactly one column")
    values = pd.to_numeric(table.iloc[:, 0], errors="raise")
    if values.isna().any() or not all(math.isfinite(float(x)) for x in values):
        raise ValueError(f"{path.name}: contains missing or non-finite RUL values")
    if (values < 0).any():
        raise ValueError(f"{path.name}: RUL values must be non-negative")
    return values


def validate_one(dataset: str) -> dict[str, Any]:
    train = load_sensor_file(RAW_DIR / f"train_{dataset}.txt")
    test = load_sensor_file(RAW_DIR / f"test_{dataset}.txt")
    rul = load_rul_file(RAW_DIR / f"RUL_{dataset}.txt")

    # In the standard training files, each engine's last observed cycle has RUL 0.
    last_cycle = train.groupby(0)[1].transform("max")
    train_rul = last_cycle - train[1]
    if (train_rul < 0).any():
        raise ValueError(f"{dataset}: derived training RUL contains negative values")
    last_rows = train[1].eq(last_cycle)
    if not train_rul.loc[last_rows].eq(0).all():
        raise ValueError(f"{dataset}: training RUL endpoint validation failed")

    train_engine_count = int(train[0].nunique())
    test_engine_count = int(test[0].nunique())
    if len(rul) != test_engine_count:
        raise ValueError(
            f"{dataset}: RUL file has {len(rul)} targets, but test file has "
            f"{test_engine_count} distinct engines"
        )

    # Basic consistency check: each engine has at least one observed cycle.
    if train.groupby(0)[1].size().min() < 1 or test.groupby(0)[1].size().min() < 1:
        raise ValueError(f"{dataset}: found an engine with no observations")

    return {
        "dataset": dataset,
        "status": "PASS",
        "train_rows": int(len(train)),
        "train_engines": train_engine_count,
        "train_cycle_min": int(train[1].min()),
        "train_cycle_max": int(train[1].max()),
        "test_rows": int(len(test)),
        "test_engines": test_engine_count,
        "test_cycle_min": int(test[1].min()),
        "test_cycle_max": int(test[1].max()),
        "rul_targets": int(len(rul)),
        "rul_min": float(rul.min()),
        "rul_max": float(rul.max()),
        "train_columns": int(train.shape[1]),
        "test_columns": int(test.shape[1]),
    }


def write_hashes() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for path in sorted(RAW_DIR.rglob("*")):
        if path.is_file():
            rows.append({
                "relative_path": str(path.relative_to(PROJECT_ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    with HASH_REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "NASA C-MAPSS structural validation",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Project root: {PROJECT_ROOT}",
        f"Raw dataset directory: {RAW_DIR}",
        "",
    ]
    summaries: list[dict[str, Any]] = []
    failures: list[str] = []

    if not RAW_DIR.is_dir():
        failures.append(f"Data directory not found: {RAW_DIR}")
    else:
        for dataset in DATASETS:
            try:
                summary = validate_one(dataset)
                summaries.append(summary)
                report_lines.extend([
                    f"{dataset}: PASS",
                    f"  Train rows/engines: {summary['train_rows']:,} / {summary['train_engines']}",
                    f"  Test rows/engines: {summary['test_rows']:,} / {summary['test_engines']}",
                    f"  Test RUL targets/range: {summary['rul_targets']} / {summary['rul_min']:g} to {summary['rul_max']:g}",
                    "",
                ])
                print(f"{dataset}: PASS")
            except Exception as exc:  # report each subset independently
                failures.append(f"{dataset}: {type(exc).__name__}: {exc}")
                report_lines.extend([f"{dataset}: FAIL", f"  {type(exc).__name__}: {exc}", ""])
                print(f"{dataset}: FAIL — {exc}")

    hash_rows: list[dict[str, str | int]] = []
    if RAW_DIR.is_dir():
        try:
            hash_rows = write_hashes()
            report_lines.append(f"SHA-256 manifest: {HASH_REPORT} ({len(hash_rows)} files)")
        except Exception as exc:
            failures.append(f"Checksum generation failed: {exc}")
            report_lines.append(f"Checksum generation FAILED: {exc}")

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_directory": str(RAW_DIR),
        "datasets": summaries,
        "failure_count": len(failures),
        "failures": failures,
        "hashed_file_count": len(hash_rows),
        "hash_manifest": str(HASH_REPORT),
    }
    JSON_REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_lines.extend(["", f"Overall status: {'PASS' if not failures and len(summaries) == 4 else 'FAIL'}"])
    report_lines.extend(f"ERROR: {failure}" for failure in failures)
    TEXT_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"\nReport: {TEXT_REPORT}")
    print(f"JSON:   {JSON_REPORT}")
    if failures or len(summaries) != 4:
        print("Validation failed. Fix the reported issue(s) before moving on.")
        return 1
    print(f"SHA-256 checksums: {HASH_REPORT}")
    print("All four subsets passed the initial structural checks.")
    print("Note: structural PASS does not prove absence of every possible data issue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
