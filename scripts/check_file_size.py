#!/usr/bin/env python3
"""Fail if any tracked Python file exceeds ~800 lines.

Enforces the repo style rule documented in AGENTS.md and the user-level
guideline "keep individual files under ~800 lines". Meant to be invoked
by pre-commit (`.pre-commit-config.yaml`) and by CI.

Exits 0 when every file passes, 1 otherwise. Files to check are either
passed on argv (pre-commit's default behaviour) or discovered by walking
the current directory when argv is empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 800

DEFAULT_ROOTS = (Path("src"), Path("tests"), Path("scripts"))


def _iter_default_targets() -> list[Path]:
    out: list[Path] = []
    for root in DEFAULT_ROOTS:
        if root.exists():
            out.extend(sorted(root.rglob("*.py")))
    return out


def _count_lines(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or _iter_default_targets()
    offenders: list[tuple[Path, int]] = []
    for path in targets:
        if path.suffix != ".py" or not path.is_file():
            continue
        n = _count_lines(path)
        if n > MAX_LINES:
            offenders.append((path, n))

    if offenders:
        print(f"file-size-guard: {len(offenders)} file(s) exceed {MAX_LINES} lines:")
        for path, n in offenders:
            print(f"  {path}: {n} lines")
        print("Refactor into smaller modules (AGENTS.md style rule).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
