#!/usr/bin/env python3
"""Enforce a coverage floor of 95% on the pure-function core.

Adapters may legitimately have live-network branches that we don't
exercise offline. The core (records, quality metrics, compare harness)
has no such excuse.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CORE_FLOOR = 95.0
CORE_MODULES = (
    "src/specint/records.py",
    "src/specint/quality/metrics.py",
    "src/specint/compare/harness.py",
    "src/specint/compare/dedupe.py",
)


def parse_coverage(path: Path) -> dict[str, float]:
    tree = ET.parse(path)
    out: dict[str, float] = {}
    for cls in tree.iterfind(".//class"):
        filename = cls.get("filename") or ""
        rate = cls.get("line-rate")
        if rate is None:
            continue
        out[filename] = float(rate) * 100.0
    return out


def main() -> int:
    cov_path = Path("coverage.xml")
    if not cov_path.exists():
        print(f"::error::{cov_path} not found; run pytest with --cov-report=xml", file=sys.stderr)
        return 1
    per_file = parse_coverage(cov_path)

    failed: list[tuple[str, float]] = []
    for target in CORE_MODULES:
        if not Path(target).exists():
            continue
        candidates = [
            v
            for k, v in per_file.items()
            if k == target or k.endswith("/" + target) or target.endswith("/" + k)
        ]
        if not candidates:
            print(f"::warning::coverage row missing for {target}", file=sys.stderr)
            continue
        pct = max(candidates)
        if pct < CORE_FLOOR:
            failed.append((target, pct))
        else:
            print(f"OK {target}: {pct:.1f}%")

    if failed:
        print(f"::error::Core-module coverage below {CORE_FLOOR:.0f}%:", file=sys.stderr)
        for name, pct in failed:
            print(f"  {name}: {pct:.1f}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
