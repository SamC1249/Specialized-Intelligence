"""Offline-only test discipline guard.

CI runs with no network, but nothing in the harness prevents a future
test from silently reaching out to the real web (e.g. by instantiating
`httpx.Client()` and calling `.get(...)`) and passing on the CI
runner's serendipitous connectivity while flaking everywhere else.

This test scans the `tests/` tree for forbidden network patterns.
Source code under `src/specint/sources/` is expected to use httpx in
`search()` — this test does NOT touch that tree.
"""

from __future__ import annotations

import re
from pathlib import Path

TESTS_ROOT = Path(__file__).parent

FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "httpx.Client(": re.compile(r"\bhttpx\.Client\s*\("),
    "httpx.AsyncClient(": re.compile(r"\bhttpx\.AsyncClient\s*\("),
    "httpx.get(": re.compile(r"\bhttpx\.get\s*\("),
    "requests.get(": re.compile(r"\brequests\.(?:get|post|put|delete|head|patch)\s*\("),
    "urllib.request.urlopen(": re.compile(r"\burlopen\s*\("),
    "socket.create_connection(": re.compile(r"\bsocket\.create_connection\s*\("),
}


def _iter_test_files() -> list[Path]:
    return [
        p
        for p in TESTS_ROOT.rglob("*.py")
        if "fixtures" not in p.parts and p.name != "conftest.py.disabled"
    ]


def test_no_live_network_calls_in_tests() -> None:
    offenders: list[str] = []
    for py in _iter_test_files():
        if py.name == Path(__file__).name:
            continue
        text = py.read_text(encoding="utf-8")
        for label, pat in FORBIDDEN_PATTERNS.items():
            if pat.search(text):
                offenders.append(f"{py.relative_to(TESTS_ROOT.parent)} :: {label}")
    assert not offenders, (
        "Tests must be offline. Found forbidden network calls:\n  - "
        + "\n  - ".join(sorted(offenders))
        + "\nUse fixtures under tests/fixtures/ and pass raw payloads to Source.parse()."
    )


def test_guard_scans_at_least_the_existing_suite() -> None:
    files = _iter_test_files()
    assert len(files) >= 5, f"expected to find at least 5 test files, saw {len(files)}"
