from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

SUBSETS = ("FD001", "FD002", "FD003", "FD004")
METHODS = (
    "RF15", "HGB15", "RF30", "HGB30",
    "equal_average", "static_OOF_inverse_MAE",
    "V1_adaptive_error_gate", "V2_nested_selected",
)

def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Read-only validation and compact V1/V2 analysis of Phase 9 nested CV outputs."
    )
    ap.add_argument("--root", default=".", help="DARE-RUL repository root")
    args = ap.parse_args()
    project = Path(args.root).resolve()
    out = project / "results" / "phase9" / "nested_validation"

    required = {
        "nested_cv_metrics.csv": 32,
        "nested_cv_predictions.csv": 160359,
    }
    loaded = {}
    failed = False
    for name, expected in required.items():
        path = out / name
        if not path.exists():
            print(f"FAIL missing {path}")
            failed = True
            continue
        rows, cols = read_csv(path)
        loaded[name] = rows
        status = "PASS" if len(rows) == expected else "FAIL"
        print(f"{status}: {name}: {len(rows)} rows (expected {expected})")
        if len(rows) != expected:
            failed = True

    param_path = out / "nested_cv_v2_parameter_selection.csv"
    meta_path = out / "nested_cv_metadata.json"
    summary_path = out / "nested_cv_summary.md"

    if not param_path.exists() or not meta_path.exists() or not summary_path.exists():
        print("FAIL: one or more parameter/metadata/summary files are missing")
        return 1

    params, param_cols = read_csv(param_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    summary_text = summary_path.read_text(encoding="utf-8-sig")

    official_loaded = (
        metadata.get("official_test_files_loaded", True)
        or metadata.get("official_test_rul_labels_loaded", True)
    )
    print(f"{'FAIL' if official_loaded else 'PASS'}: official test files/labels loaded = {official_loaded}")
    if official_loaded:
        failed = True

    subsets_meta = metadata.get("subsets", [])
    outer_count = 0
    fallback_count = 0
    shrinkages = []
    for item in subsets_meta:
        folds = item.get("outer_folds", [])
        outer_count += len(folds)
        for fold in folds:
            fallback_count += int(fold.get("v2_fallback_rows", 0))
            shrinkages.append(float(fold.get("selected_v2_parameters", {}).get("shrinkage", float("nan"))))

    print(f"{'PASS' if outer_count == 20 else 'FAIL'}: outer fold records = {outer_count} (expected 20)")
    print(f"{'PASS' if fallback_count == 0 else 'REVIEW'}: total V2 fallback rows = {fallback_count}")
    if outer_count != 20:
        failed = True

    if len(params) != 720:
        print(f"REVIEW: parameter-selection rows = {len(params)} (expected 720 from 36 candidates × 5 folds × 4 subsets)")
    else:
        print("PASS: parameter-selection rows = 720")

    if shrinkages and all(abs(x) < 1e-12 for x in shrinkages):
        print("FINDING: every outer fold selected shrinkage = 0.0; V2 collapses to/closely reproduces V1.")
    else:
        print("FINDING: at least one outer fold selected non-zero shrinkage; inspect selected parameters.")

    metrics = loaded.get("nested_cv_metrics.csv", [])
    index = {(r.get("subset"), r.get("method")): r for r in metrics}
    print("\nV1 vs nested-selected V2 (V2 minus V1; positive error delta favours V1)")
    print("Subset  dRMSE       dMAE        dNASA-mean")
    for subset in SUBSETS:
        a = index.get((subset, "V1_adaptive_error_gate"))
        b = index.get((subset, "V2_nested_selected"))
        if not a or not b:
            print(f"{subset}: missing V1/V2 row")
            failed = True
            continue
        dr = float(b["rmse"]) - float(a["rmse"])
        dm = float(b["mae"]) - float(a["mae"])
        dn = float(b["nasa_score_mean"]) - float(a["nasa_score_mean"])
        print(f"{subset:6s} {dr:+.10f} {dm:+.10f} {dn:+.10f}")

    expected_subsets = {r.get("subset") for r in metrics}
    expected_methods = {r.get("method") for r in metrics}
    if expected_subsets != set(SUBSETS):
        print(f"FAIL: metrics subsets = {sorted(expected_subsets)}")
        failed = True
    if expected_methods != set(METHODS):
        print(f"FAIL: metrics methods = {sorted(expected_methods)}")
        failed = True

    print("\nMetadata notes:")
    print(f"status={metadata.get('status')}")
    print(f"rul_cap={metadata.get('rul_cap')} (provisional until research protocol closure)")
    print(f"seed={metadata.get('seed')}; outer={metadata.get('outer_folds')}; inner={metadata.get('inner_oof_folds')}; gate-selection={metadata.get('gate_selection_folds')}")
    elapsed = metadata.get("elapsed_seconds")
    if elapsed is not None:
        print(f"recorded elapsed_seconds={elapsed}; verify timer semantics before reporting as compute runtime")

    print("\nPHASE 9 NESTED-VALIDATION OUTPUT CHECK " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
