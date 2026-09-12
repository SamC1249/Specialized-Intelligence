#!/usr/bin/env python3
"""Fail if any listed file exceeds the ~800 LOC/file rule from AGENTS.md.

Called by the local `check-file-length` pre-commit hook. Reports every
offender at once so a single push surfaces all violations, not just the
first.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 800


def main(argv: list[str]) -> int:
    offenders: list[tuple[str, int]] = []
    for arg in argv:
        p = Path(arg)
        if not p.is_file():
            continue
        try:
            n = sum(1 for _ in p.open("rb"))
        except OSError:
            continue
        if n > MAX_LINES:
            offenders.append((str(p), n))
    if not offenders:
        return 0
    for path, n in offenders:
        print(f"{path}: {n} lines (> {MAX_LINES}); split it per AGENTS.md.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
