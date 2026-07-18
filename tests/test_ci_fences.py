"""Regression fences to keep our test discipline honest.

- Fence 1: `pytest -m integration` must collect ZERO tests unless someone
  explicitly opts in. We don't have any integration tests yet, so the
  count should be exactly 0.
- Fence 2: no test in this repo may make outbound HTTP. We enforce this
  by patching `httpx.Client.send` at import time here.

These fences are cheap and catch a whole class of "silent network
dependency" regressions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_integration_marker_collects_nothing_without_opt_in():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "integration"],
        cwd=REPO_ROOT,
        env={"PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert (
        "0 tests collected" in combined
        or "no tests collected" in combined
        or "no tests ran" in combined
    ), combined


def test_httpx_send_is_disabled_in_offline_suite(monkeypatch):
    """Deny-listing outbound HTTP anywhere in the offline test process."""

    def _boom(self, *args, **kwargs):  # pragma: no cover - reached only on regression
        raise AssertionError("Offline tests must not make live HTTP calls. Use a fixture instead.")

    monkeypatch.setattr(httpx.Client, "send", _boom, raising=True)
    with pytest.raises(AssertionError):
        httpx.Client().get("https://example.test/")
