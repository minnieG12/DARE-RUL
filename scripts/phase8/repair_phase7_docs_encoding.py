"""Repair mojibake introduced when PowerShell 5.1 rewrote Phase 7 Markdown.

It only touches project Markdown files known to have been rewritten by the old
helper. Existing wording is retained; common UTF-8-as-Windows-1252 sequences are
repaired, UTF-8 BOMs are removed, and excess blank lines at EOF are trimmed.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    ROOT / "README.md",
    ROOT / "docs" / "project" / "research_log.md",
    ROOT / "docs" / "project" / "phase7_streaming_benchmark_summary.md",
)
REPLACEMENTS = {
    "â€“": "–",
    "â€”": "—",
    "â†’": "→",
    "â€™": "’",
    "â€˜": "‘",
    "â€œ": "“",
    "â€�": "”",
    "Â·": "·",
}


def repair(text: str) -> tuple[str, int]:
    count = 0
    for wrong, right in REPLACEMENTS.items():
        occurrences = text.count(wrong)
        if occurrences:
            text = text.replace(wrong, right)
            count += occurrences
    # Normalize line endings and remove trailing whitespace/blank lines only.
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n", count


def main() -> int:
    total = 0
    for path in FILES:
        if not path.exists():
            print(f"SKIP (not found): {path.relative_to(ROOT)}")
            continue
        original = path.read_text(encoding="utf-8-sig")
        corrected, count = repair(original)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(corrected)
        total += count
        print(f"Rewrote UTF-8 Markdown: {path.relative_to(ROOT)}; corrected mojibake sequences: {count}")
    print(f"Phase 7 documentation encoding cleanup complete; corrected {total} sequences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
