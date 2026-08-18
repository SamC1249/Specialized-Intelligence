#!/usr/bin/env python3
"""Fail if any file under tests/ imports httpx or hits a live network URL.

Rule from AGENTS.md constraint 4: "Reproducible offline tests. CI must
pass without network. Use fixtures in `tests/fixtures/`, never live HTTP
in unit tests."

Allowed:
  - URL strings inside `tests/fixtures/**` (they are inert JSON/HTML).
  - URL strings under `pytest.mark.integration`-marked files, when the
    file also imports the marker.

Disallowed:
  - `import httpx` in `tests/**`.
  - `httpx.get/post`, `requests.get/post`, `urllib.request.urlopen` in
    any offline test.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEST_ROOT = Path("tests")
BANNED_IMPORTS = (
    re.compile(r"^\s*import\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*from\s+httpx\s+import", re.MULTILINE),
    re.compile(r"^\s*import\s+requests\b", re.MULTILINE),
    re.compile(r"^\s*from\s+requests\s+import", re.MULTILINE),
)
BANNED_CALLS = (
    re.compile(r"httpx\.(get|post|put|delete|request)\("),
    re.compile(r"requests\.(get|post|put|delete|request)\("),
    re.compile(r"urllib\.request\.urlopen\("),
)


def is_integration_file(text: str) -> bool:
    return "pytest.mark.integration" in text


def main() -> int:
    if not TEST_ROOT.exists():
        print("no tests/ directory; skipping")
        return 0

    offenders: list[str] = []
    for path in TEST_ROOT.rglob("*.py"):
        if "fixtures" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if is_integration_file(text):
            continue
        for pat in BANNED_IMPORTS + BANNED_CALLS:
            m = pat.search(text)
            if m:
                offenders.append(f"{path}: banned pattern {m.group(0)!r}")
                break

    if offenders:
        print("::error::Live-network usage detected in offline tests:", file=sys.stderr)
        for line in offenders:
            print(f"  {line}", file=sys.stderr)
        print(
            "Mark the file with `pytest.mark.integration` and only run it under "
            "SPECINT_RUN_INTEGRATION=1.",
            file=sys.stderr,
        )
        return 1
    print("OK: no live network usage in offline tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
