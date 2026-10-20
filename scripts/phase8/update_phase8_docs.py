"""Generate Phase 8 curated documentation without trusting a CLI approval flag.

Reads local Phase 8 artifacts and updates README.md, docs/project/research_log.md,
and docs/project/phase8_final_test_summary.md. It does not modify predictions,
metrics, or run_metadata.json. Approval is considered VERIFIED only when a
separate, reviewed docs/project/phase8_protocol_approval.md record explicitly
contains the expected fields; the run's --ProtocolApproved flag alone is not
sufficient evidence.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "phase8"
README = ROOT / "README.md"
RESEARCH_LOG = ROOT / "docs" / "project" / "research_log.md"
SUMMARY = ROOT / "docs" / "project" / "phase8_final_test_summary.md"
APPROVAL_RECORD = ROOT / "docs" / "project" / "phase8_protocol_approval.md"

README_START = "<!-- BEGIN DARE-RUL PHASE 8 STATUS -->"
README_END = "<!-- END DARE-RUL PHASE 8 STATUS -->"
LOG_START = "<!-- BEGIN DARE-RUL PHASE 8 RECORD -->"
LOG_END = "<!-- END DARE-RUL PHASE 8 RECORD -->"
EXPECTED_SUBSETS = {"FD001", "FD002", "FD003", "FD004"}
EXPECTED_COUNTS = {
    "test_predictions.csv": 707,
    "test_scored_predictions.csv": 707,
    "maintenance_recommendations.csv": 707,
    "final_test_metrics.csv": 4,
    "oof_fold_audit.csv": 20,
}


def replace_managed_block(path: Path, start_marker: str, end_marker: str, body: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required document is missing: {path}")
    text = path.read_text(encoding="utf-8-sig")
    block = f"{start_marker}\n{body.strip()}\n{end_marker}"
    if start_marker in text and end_marker in text:
        begin = text.index(start_marker)
        finish = text.index(end_marker, begin) + len(end_marker)
        text = text[:begin] + block + text[finish:]
    else:
        text = text.rstrip() + "\n\n" + block
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def approval_status() -> tuple[bool, str]:
    """Never infer real approval from run_metadata.json's CLI Boolean alone."""
    if not APPROVAL_RECORD.exists():
        return False, "No independent approval record is present in the repository."
    text = APPROVAL_RECORD.read_text(encoding="utf-8-sig")
    required = {
        "Approval status: VERIFIED",
        "Decision date:",
        "Evidence reference:",
    }
    if not all(token in text for token in required):
        return False, "The approval record is missing required fields or VERIFIED status."
    # Require non-placeholder values after the labels; a heading alone is not evidence.
    for label in ("Decision date:", "Evidence reference:"):
        line = next((line.strip() for line in text.splitlines() if line.strip().startswith(label)), "")
        value = line[len(label):].strip()
        if not value or any(word in value.lower() for word in ("todo", "tbd", "fill", "placeholder", "unknown")):
            return False, f"The approval record has no usable value for {label}"
    return True, "Approval record marked VERIFIED; human review of its authenticity is still required."


def expected_row_count(name: str) -> int:
    path = RESULTS / name
    if not path.exists():
        raise FileNotFoundError(f"Missing Phase 8 artifact: {path}")
    return len(pd.read_csv(path))


def main() -> int:
    metadata_path = RESULTS / "run_metadata.json"
    metrics_path = RESULTS / "final_test_metrics.csv"
    predictions_path = RESULTS / "test_predictions.csv"
    scored_path = RESULTS / "test_scored_predictions.csv"
    for path in (metadata_path, metrics_path, predictions_path, scored_path):
        if not path.exists():
            raise SystemExit(f"ERROR: required Phase 8 artifact is missing: {path}")

    metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
    metrics = pd.read_csv(metrics_path)
    if metadata.get("status") != "PASS" or set(metrics["subset"].astype(str)) != EXPECTED_SUBSETS:
        raise SystemExit("ERROR: expected PASS metadata and metrics for FD001, FD002, FD003, FD004.")
    if metadata.get("official_test_targets_used_for_training_or_selection") is not False:
        raise SystemExit("ERROR: metadata does not establish test targets were excluded from training/selection.")

    counts = {name: expected_row_count(name) for name in EXPECTED_COUNTS}
    for name, expected in EXPECTED_COUNTS.items():
        if counts[name] != expected:
            raise SystemExit(f"ERROR: {name} has {counts[name]} rows; expected {expected}. No docs updated.")

    predictions = pd.read_csv(predictions_path, nrows=1)
    if any(c in predictions.columns for c in ("RUL_true", "RUL", "error_pred_minus_true")):
        raise SystemExit("ERROR: test_predictions.csv contains target/scoring columns; refusing docs update.")

    verified, approval_note = approval_status()
    cap = int(metadata.get("training_rul_cap", 125))
    if verified:
        protocol_line = f"Protocol approval: recorded as VERIFIED in `{APPROVAL_RECORD.relative_to(ROOT).as_posix()}`. Confirm the linked evidence is genuine and dated before scoring."
        cap_line = f"Training RUL cap: {cap} cycles."
        status_text = "Execution PASS; protocol approval record is marked VERIFIED (human verification required)."
    else:
        protocol_line = f"Protocol approval: **UNVERIFIED**. {approval_note} The CLI flag in run metadata is not independent evidence. Treat these scores as exploratory pending protocol closure."
        cap_line = f"Training RUL cap: {cap} cycles (provisional for research interpretation pending protocol closure)."
        status_text = "Execution PASS; protocol approval evidence not verified, so interpret scores as exploratory."

    metrics = metrics.sort_values("subset")
    table = [
        "| Subset | Frozen method | Engines | RMSE | MAE | NASA score sum | NASA score mean |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in metrics.to_dict("records"):
        table.append(
            f"| {row['subset']} | `{row['selected_method']}` | {int(row['test_engines'])} | "
            f"{float(row['rmse']):.4f} | {float(row['mae']):.4f} | "
            f"{float(row['nasa_score_sum']):.4f} | {float(row['nasa_score_mean']):.6f} |"
        )

    summary = "\n".join([
        "# Phase 8 — C-MAPSS test-cohort evaluation summary",
        "",
        f"**Execution status:** {metadata.get('status')}. **Interpretation status:** {status_text}",
        "",
        "## Procedure recorded by the implementation",
        "",
        f"- {cap_line}",
        f"- OOF folds: {int(metadata.get('oof_folds', 5))} engine-grouped folds over labeled training engines.",
        "- The four final experts were fitted on labeled training engines; gate models were trained from engine-grouped OOF predictions only.",
        "- Frozen per-subset methods: FD001/FD004 `cross_window_no_disagreement`; FD002/FD003 `cross_window_error_gate`.",
        "- The generated run summary states prediction-only outputs were written before official targets were read for scoring. Official test targets were used for scoring only, not fitting/method selection.",
        "- Test targets were scored uncapped; model predictions were clipped to the training cap.",
        "",
        "## Results recorded by this run",
        "",
        *table,
        "",
        "Artifact row counts: " + ", ".join(f"`{k}` = {v}" for k, v in counts.items()) + ".",
        "",
        "## Protocol status",
        "",
        protocol_line,
        "",
        "Do not change models, gates, cap, features, thresholds or method selections in response to these scores and still describe the same cohort as an untouched test set. Any future changes must use training/validation-only evidence.",
        "",
        "## Limitations",
        "",
        "- These are benchmark results for the NASA C-MAPSS simulated dataset, not validation on real aircraft.",
        "- The current stream benchmark is a local setup with one Spark worker and one HDFS DataNode. It does not establish horizontal scalability, high availability, or failure recovery.",
        "- CRITICAL/HIGH/MONITOR maintenance-demo tiers are illustrative rules, not approved aircraft maintenance policy.",
        "- The transcript reports an elapsed time of 443454.516 seconds (~5.13 days), which is suspicious for a one-shot run; do not publish that runtime until its provenance is understood.",
        "",
        "## Local generated artifacts (not normally committed)",
        "",
        *[f"- `results/phase8/{name}`" for name in EXPECTED_COUNTS],
        "- `results/phase8/run_metadata.json`",
        "- `models/phase8/`",
    ])
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(summary + "\n", encoding="utf-8", newline="\n")

    readme_body = "\n".join([
        "## Phase 8 — Evaluation run executed",
        "",
        "The Phase 8 test-cohort evaluation was executed on all four NASA C-MAPSS subsets, producing predictions and scored summaries for 707 test engines. See [`docs/project/phase8_final_test_summary.md`](docs/project/phase8_final_test_summary.md) for method mapping, metrics and limitations.",
        "",
        f"**Status:** {status_text}",
        "",
        "The prediction-only CSV was written before test targets were read for scoring according to the generated run summary. Do not use these scores to tune the models and still describe the cohort as untouched.",
        "",
        "The maintenance demo uses illustrative risk bands only; this is not approved aviation maintenance guidance.",
    ])
    replace_managed_block(README, "<!-- BEGIN DARE-RUL PHASE 8 STATUS -->", "<!-- END DARE-RUL PHASE 8 STATUS -->", readme_body)

    log_body = "\n".join([
        f"## Phase 8 — Test-cohort evaluation and maintenance demo ({date.today().isoformat()})",
        "",
        f"- Execution status: {metadata.get('status')}; artifact counts were validated: {counts}.",
        "- Frozen method mapping: FD001/FD004 `cross_window_no_disagreement`; FD002/FD003 `cross_window_error_gate`.",
        "- Metrics and caveats are documented in `docs/project/phase8_final_test_summary.md`.",
        f"- {protocol_line}",
        "- The generated run summary says predictions were saved before test targets were opened for scoring; do not tune on this cohort after observing results.",
        "- Phase 8 maintenance demo passed; risk bands are illustrative only.",
        "- Current streaming evidence remains local/single-worker/single-DataNode; do not claim production real-time, HA, or horizontal scaling.",
    ])
    replace_managed_block(RESEARCH_LOG, LOG_START, LOG_END, log_body)
    print(f"Phase 8 docs updated (safe approval interpretation: {'VERIFIED-record-present' if verified else 'UNVERIFIED'}).")
    print(f"Summary: {SUMMARY}")
    print("Review README/research-log diff and approval record before committing; outputs/models were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
