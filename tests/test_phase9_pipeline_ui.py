from pathlib import Path

from dashboard.pipeline import parse_streaming_benchmark_text, read_streaming_benchmark


def _summary():
    return """# Streaming Benchmark

| Requested messages | Delivered | Valid HDFS rows | Invalid rows | Duplicate engine-cycle pairs | Cycle-order warnings | Spark/HDFS elapsed (s) | Approx. end-to-end rows/s | Status |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 500 | 500 | 500 | 0 | 0 | 0 | 29.33 | 17.05 | PASS |
| 5000 | 5000 | 5000 | 0 | 0 | 0 | 59.35 | 84.25 | PASS |
| 20000 | 20000 | 20000 | 0 | 0 | 0 | 151.77 | 131.78 | PASS |

## Notes
Old phase title and narrative text must not be rendered in the dashboard.
"""


def test_parser_extracts_only_benchmark_rows_and_normalizes_numbers():
    frame = parse_streaming_benchmark_text(_summary())
    assert frame["requested_messages"].tolist() == [500, 5000, 20000]
    assert frame["delivered"].tolist() == [500, 5000, 20000]
    assert frame["rows_per_second"].tolist() == [17.05, 84.25, 131.78]
    assert frame["workload_label"].tolist() == ["500", "5,000", "20,000"]
    assert (frame["status"] == "PASS").all()


def test_parser_rejects_summary_without_results_table():
    try:
        parse_streaming_benchmark_text("# Benchmark\nNo results table here")
    except ValueError as exc:
        assert "results table" in str(exc)
    else:
        raise AssertionError("Expected parser to reject missing result table")


def test_reader_loads_curated_summary(tmp_path: Path):
    path = tmp_path / "benchmark.md"
    path.write_text(_summary(), encoding="utf-8")
    frame = read_streaming_benchmark(path)
    assert len(frame) == 3
    assert frame.iloc[-1]["elapsed_seconds"] == 151.77
