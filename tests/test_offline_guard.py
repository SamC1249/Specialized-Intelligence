"""Offline discipline guard.

Fails if any file under `tests/` (except `tests/fixtures/`) uses a live
networking primitive. Rationale:

    AGENTS.md hard constraint #4 — "Reproducible offline tests. CI must
    pass without network. Use fixtures in tests/fixtures/, never live
    HTTP in unit tests."

The check is a rule-based grep because the goal is a *tripwire*, not a
type system: a maintainer that reaches for `requests.get(...)` in a
unit test should fail fast, right at the import.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_FORBIDDEN_IN_TESTS: tuple[tuple[str, str], ...] = (
    ("httpx.Client(", "use fixtures under tests/fixtures/"),
    ("httpx.AsyncClient(", "use fixtures under tests/fixtures/"),
    ("httpx.get(", "use fixtures under tests/fixtures/"),
    ("httpx.post(", "use fixtures under tests/fixtures/"),
    ("requests.get(", "use fixtures under tests/fixtures/"),
    ("requests.post(", "use fixtures under tests/fixtures/"),
    ("urllib.request.urlopen", "use fixtures under tests/fixtures/"),
    ("urlopen(", "use fixtures under tests/fixtures/"),
    ("socket.create_connection", "no direct sockets in offline tests"),
)

_ALLOWED_PATH_MARKERS: tuple[str, ...] = (
    "tests/fixtures/",
    "tests/test_offline_guard.py",
)


def _is_allowed(path: Path) -> bool:
    posix = path.as_posix()
    return any(marker in posix for marker in _ALLOWED_PATH_MARKERS)


def test_no_live_network_calls_in_tests() -> None:
    tests_dir = REPO / "tests"
    offenders: list[str] = []
    for py in tests_dir.rglob("*.py"):
        if _is_allowed(py):
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for needle, reason in _FORBIDDEN_IN_TESTS:
            if needle in text:
                offenders.append(f"{py.relative_to(REPO)}: '{needle}' — {reason}")
    assert not offenders, "Live-network usage detected in offline test suite:\n  " + "\n  ".join(
        offenders
    )


def test_no_accidental_pytest_mark_network() -> None:
    tests_dir = REPO / "tests"
    pat = re.compile(r"pytest\.mark\.network|@network\b")
    offenders: list[str] = []
    for py in tests_dir.rglob("*.py"):
        if _is_allowed(py) or py.name == "test_offline_guard.py":
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if pat.search(text):
            offenders.append(py.relative_to(REPO).as_posix())
    assert not offenders, (
        "Use the documented `integration` marker (SPECINT_RUN_INTEGRATION=1), "
        "not ad-hoc `network` markers. Offenders: " + ", ".join(offenders)
    )
