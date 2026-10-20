"""Check that saved Phase 8 models/gates reproduce saved predictions for selected engines."""
from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.ensemble_service import SavedEnsembleService  # noqa: E402

SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subsets", nargs="+", choices=SUBSETS, default=list(SUBSETS))
    p.add_argument("--engines-per-subset", type=int, default=1)
    p.add_argument("--tolerance", type=float, default=1e-4)
    args = p.parse_args()
    if args.engines_per_subset < 1 or args.tolerance <= 0:
        raise SystemExit("engines-per-subset and tolerance must be positive")
    service = SavedEnsembleService(ROOT)
    failures = []
    for subset in args.subsets:
        engines = service.test_engines(subset)[:args.engines_per_subset]
        for engine in engines:
            try:
                report = service.parity_report(subset, int(engine), tolerance=args.tolerance)
                print(f"{subset} engine {engine}: {'PASS' if report['passed'] else 'FAIL'}; abs diff={report['absolute_difference']:.8g}")
                if not report["passed"]:
                    failures.append({"subset": subset, "engine_id": engine, **report})
            except Exception as exc:
                failures.append({"subset": subset, "engine_id": engine, "error": str(exc)})
        service._bundles.clear()
        gc.collect()
    if failures:
        print("PARITY CHECK FAILED. Do not display SHAP explanations until resolved.")
        for failure in failures:
            print(failure)
        return 1
    print("PHASE 9 MODEL PARITY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
