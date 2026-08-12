from __future__ import annotations

import json
import os
import socket
from pathlib import Path

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


class _BlockedNetworkError(RuntimeError):
    """Raised when unit-test code attempts a real outbound TCP connect."""


_ALLOWED_HOSTS = frozenset(
    {
        "127.0.0.1",
        "::1",
        "localhost",
    }
)


def _guarded_getaddrinfo(host, *args, **kwargs):  # type: ignore[no-untyped-def]
    if host not in _ALLOWED_HOSTS:
        raise _BlockedNetworkError(
            f"unit tests must be offline; refused DNS lookup for {host!r}. "
            "Set SPECINT_RUN_INTEGRATION=1 to allow."
        )
    return _real_getaddrinfo(host, *args, **kwargs)


def _guarded_socket_connect(self, address):  # type: ignore[no-untyped-def]
    host = address[0] if isinstance(address, tuple) else str(address)
    if host not in _ALLOWED_HOSTS:
        raise _BlockedNetworkError(
            f"unit tests must be offline; refused TCP connect to {host!r}. "
            "Set SPECINT_RUN_INTEGRATION=1 to allow."
        )
    return _real_socket_connect(self, address)


_real_getaddrinfo = socket.getaddrinfo
_real_socket_connect = socket.socket.connect


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block outbound TCP connects and DNS lookups during unit tests.

    Skipped when `SPECINT_RUN_INTEGRATION=1` so the same suite can be
    reused as an integration harness against live endpoints.
    """
    if os.environ.get("SPECINT_RUN_INTEGRATION") == "1":
        return
    monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", _guarded_socket_connect)
