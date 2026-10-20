"""Parse the maintained streaming benchmark table for dashboard presentation."""
from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

_HEADER_MAP = {
    "requested messages": "requested_messages",
    "delivered": "delivered",
    "valid hdfs rows": "valid_hdfs_rows",
    "invalid rows": "invalid_rows",
    "duplicate engine-cycle pairs": "duplicate_engine_cycle_pairs",
    "cycle-order warnings": "cycle_order_warnings",
    "spark/hdfs elapsed (s)": "elapsed_seconds",
    "approx. end-to-end rows/s": "rows_per_second",
    "status": "status",
}
_NUMERIC_COLUMNS = [c for c in _HEADER_MAP.values() if c != "status"]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_streaming_benchmark_text(text: str) -> pd.DataFrame:
    """Extract only the benchmark results table, not the document's phase heading or notes."""
    lines = text.splitlines()
    header_index = None
    for i, line in enumerate(lines):
        lower = line.lower()
        if "requested messages" in lower and "valid hdfs rows" in lower and line.strip().startswith("|"):
            header_index = i
            break
    if header_index is None:
        raise ValueError("Could not locate the streaming benchmark results table")

    raw_headers = [h.lower().replace("**", "").strip() for h in _cells(lines[header_index])]
    if not all(header in _HEADER_MAP for header in raw_headers):
        raise ValueError(f"Unexpected streaming benchmark columns: {raw_headers}")
    expected = list(_HEADER_MAP)
    if raw_headers != expected:
        # Accept only the known columns, but preserve the canonical dashboard schema.
        if set(raw_headers) != set(expected):
            raise ValueError(f"Streaming benchmark columns differ from the expected schema: {raw_headers}")

    records: list[dict] = []
    for line in lines[header_index + 1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if records:
                break
            continue
        cells = _cells(stripped)
        if not cells or all(re.fullmatch(r":?-{3,}:?", c or "-") for c in cells):
            continue
        if len(cells) != len(raw_headers):
            continue
        values = dict(zip(raw_headers, cells))
        try:
            int(values["requested messages"])
        except (KeyError, ValueError):
            continue
        record = {_HEADER_MAP[key]: value for key, value in values.items()}
        records.append(record)

    if not records:
        raise ValueError("Streaming benchmark results table contains no data rows")

    frame = pd.DataFrame(records)
    for col in _NUMERIC_COLUMNS:
        frame[col] = pd.to_numeric(frame[col].astype(str).str.replace(",", "", regex=False), errors="raise")
    frame["status"] = frame["status"].astype(str).str.upper()
    frame["workload_label"] = frame["requested_messages"].map(lambda n: f"{int(n):,}")
    frame = frame.sort_values("requested_messages", kind="stable").reset_index(drop=True)
    return frame


def read_streaming_benchmark(path: str | Path) -> pd.DataFrame:
    """Read the benchmark table from the curated project Markdown summary."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark summary not found: {path}")
    return parse_streaming_benchmark_text(path.read_text(encoding="utf-8-sig"))
