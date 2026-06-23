"""Pre-commit hook: fail if any staged Python file exceeds 800 LOC.

User rule: keep ~800 lines of code per file max. We enforce a hard cap
of 800 lines (any kind: code, comment, blank) — files that need more
should be split.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 800


def main(paths: list[str]) -> int:
    bad: list[tuple[str, int]] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file() or p.suffix != ".py":
            continue
        n = sum(1 for _ in p.open("rb"))
        if n > MAX_LINES:
            bad.append((str(p), n))
    if bad:
        print("error: the following files exceed the 800-line cap:", file=sys.stderr)
        for path, n in bad:
            print(f"  {path}: {n} lines", file=sys.stderr)
        print("split the file. see AGENTS.md section 4.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
