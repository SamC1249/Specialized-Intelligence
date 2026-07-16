#!/usr/bin/env python3
"""Pre-commit hook: fail if any file under tests/ (excluding fixtures/)
uses a known live-network call. Keeps CI reproducible and deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

PATTERNS: dict[str, re.Pattern[str]] = {
    "httpx.Client(": re.compile(r"\bhttpx\.Client\s*\("),
    "httpx.AsyncClient(": re.compile(r"\bhttpx\.AsyncClient\s*\("),
    "httpx.get(": re.compile(r"\bhttpx\.get\s*\("),
    "requests.get(": re.compile(r"\brequests\.(?:get|post|put|delete|head|patch)\s*\("),
    "urllib.request.urlopen(": re.compile(r"\burlopen\s*\("),
    "socket.create_connection(": re.compile(r"\bsocket\.create_connection\s*\("),
}


def main() -> int:
    if not TESTS.is_dir():
        return 0
    offenders: list[str] = []
    for py in TESTS.rglob("*.py"):
        if "fixtures" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        for label, pat in PATTERNS.items():
            if pat.search(text) and py.name not in {
                "test_offline_guard.py",
            }:
                offenders.append(f"{py.relative_to(ROOT)} :: {label}")
    if offenders:
        sys.stderr.write(
            "tests/ must be offline. Forbidden network calls found:\n  - "
            + "\n  - ".join(sorted(offenders))
            + "\nUse fixtures under tests/fixtures/ and pass raw payloads to Source.parse().\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
