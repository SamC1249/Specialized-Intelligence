from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def load_json(fixtures_dir: Path):
    def _load(rel: str):
        return json.loads((fixtures_dir / rel).read_text())

    return _load


@pytest.fixture
def load_text(fixtures_dir: Path):
    def _load(rel: str) -> str:
        return (fixtures_dir / rel).read_text()

    return _load


class _NetworkDisabledError(RuntimeError):
    """Raised when a test accidentally attempts real network I/O."""


def _blocked_httpx_send(*_args, **_kwargs):
    raise _NetworkDisabledError(
        "network access is disabled inside the offline test suite; "
        "use fixtures instead. Gate any real integration test with "
        "the `integration` marker + SPECINT_RUN_INTEGRATION=1."
    )


def _blocked_socket_connect(*_args, **_kwargs):
    raise _NetworkDisabledError("socket.connect blocked inside offline test suite.")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch, request):
    """Fail loudly if any test does real network I/O.

    Skipped when either:
      - the test is marked `integration` AND SPECINT_RUN_INTEGRATION=1, or
      - the environment variable SPECINT_ALLOW_NETWORK=1 is set (escape
        hatch for local debugging only).
    """
    if os.environ.get("SPECINT_ALLOW_NETWORK") == "1":
        return
    if (
        request.node.get_closest_marker("integration") is not None
        and os.environ.get("SPECINT_RUN_INTEGRATION") == "1"
    ):
        return

    monkeypatch.setattr(httpx.Client, "send", _blocked_httpx_send)
    monkeypatch.setattr(httpx.AsyncClient, "send", _blocked_httpx_send)
    monkeypatch.setattr(socket.socket, "connect", _blocked_socket_connect)
