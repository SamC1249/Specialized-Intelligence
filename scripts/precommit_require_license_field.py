#!/usr/bin/env python3
"""Pre-commit hook: every source adapter must declare a license-confidence field.

Rationale: the day-one plan (docs/plan/2026-06-20.md §7.6) and the
PeerTube adapter recipe (docs/artifacts/peertube-federated-crawl.md)
require every adapter to expose both a `license` enum and a
`license_confidence` numeric field, so downstream filters can apply
threshold-based exclusion. This hook prevents a new adapter from landing
without the contract.

Adapter files are anything under `components/sources/` whose name is
not `__init__.py` and ends in `.py`.

The hook is intentionally lightweight: it greps for both the string
literal `"license"` and the string literal `"license_confidence"` (or
`license_confidence` as an identifier). If a candidate file has the
first but not the second, we fail.

Inputs:   pre-commit-supplied list of file paths.
Outputs:  exit 0 on success, 1 on first violation with an explanatory
          message.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LICENSE_TOK = re.compile(r"\blicense\b", re.IGNORECASE)
CONFIDENCE_TOK = re.compile(r"\blicense[_-]?confidence\b", re.IGNORECASE)

ADAPTER_SEGMENT = "components/sources/"


def is_adapter(p: Path) -> bool:
    s = p.as_posix()
    if ADAPTER_SEGMENT not in s:
        return False
    if not p.name.endswith(".py"):
        return False
    return p.name != "__init__.py"


def main(argv: list[str]) -> int:
    files = [Path(p) for p in argv[1:]]
    violations: list[Path] = []
    for fp in files:
        if not is_adapter(fp) or not fp.exists():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not LICENSE_TOK.search(text):
            continue
        if not CONFIDENCE_TOK.search(text):
            violations.append(fp)
    if violations:
        print(
            "require-license-field: source adapter is missing 'license_confidence'.\n"
            "Every file in components/sources/<name>.py that mentions 'license'\n"
            "must also expose a 'license_confidence' field (numeric in [0, 1])\n"
            "so downstream filters can threshold-exclude low-confidence rows.\n"
            "See docs/artifacts/peertube-federated-crawl.md §'Concrete recipe'.\n",
            file=sys.stderr,
        )
        for fp in violations:
            print(f"  {fp}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
