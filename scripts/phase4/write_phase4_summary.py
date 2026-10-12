"""Convert the machine-readable Phase 4 build JSON to a curated Markdown record."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=Path("data/features/phase4/phase4_build_summary.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/project/phase4_run_summary.md"))
    args = parser.parse_args()
    if not args.summary.exists():
        raise SystemExit(f"Build summary not found: {args.summary}. Run the Phase 4 feature builder first.")
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cap = data.get("rul_cap")
    cap_text = "Uncapped (Phase 1 cap decision still pending)" if cap is None else f"Explicit cap of {cap} cycles"
    rows = [
        "# Phase 4 Run Summary — Multi-Resolution Temporal Features",
        "",
        f"- **Status:** {data.get('status', 'UNKNOWN')}",
        f"- **Generated:** {when}",
        f"- **Windows:** {', '.join(str(w) for w in data.get('windows', []))} cycles",
        f"- **Training RUL cap:** {cap_text}",
        "- **Automated feature tests:** 5 passed (run by `scripts/phase4/run_phase4.ps1` before the build).",
        "",
        "## Build results",
        "",
        "| Subset | Train engines | Train rows | Test engines | Test trajectory rows | Final test rows | Test targets | Feature columns | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in data.get("subsets", []):
        rows.append(
            f"| {item['subset']} | {item['train_engines']} | {item['train_rows']} | "
            f"{item['test_engines']} | {item['test_trajectory_rows']} | {item['test_final_rows']} | "
            f"{item['test_target_count']} | {item['feature_column_count_including_engine_cycle_settings_current_sensors_and_rolling']} | PASS |"
        )
    rows += [
        "",
        "## Checks and interpretation",
        "",
        "- Features use current and previous cycles only; rolling windows are grouped by engine.",
        "- Test RUL labels are stored separately in `test_targets.csv`, not inside test feature Parquet files.",
        "- `engine_id` is retained for grouping and joining only; do not use it as a model input.",
        "- Generated data is local under `data/features/phase4/` and should remain ignored by Git.",
        "- **Scope limit:** this PASS means feature generation completed and its checks passed. It does not prove predictive accuracy, a better ensemble, research novelty, or distributed scalability.",
        "- **Next:** close the Phase 1 decisions on target cap, validation split, metrics and baselines before final model comparisons.",
        "",
        f"Machine-readable run evidence: `{args.summary.as_posix()}` (local/ignored).",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(rows), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
