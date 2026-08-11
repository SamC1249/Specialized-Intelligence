from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

try:
    from pytest_socket import disable_socket, enable_socket
except ImportError:  # pragma: no cover - dev dep should always be installed
    disable_socket = enable_socket = None  # type: ignore[assignment]


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Enforce AGENTS.md constraint #4: unit tests must not hit the network.

    Live-network tests must be explicitly marked `integration` *and* opted
    into via `SPECINT_RUN_INTEGRATION=1`.
    """
    if disable_socket is None:
        return
    if "integration" in {m.name for m in item.iter_markers()}:
        if os.environ.get("SPECINT_RUN_INTEGRATION") == "1":
            enable_socket()
        else:
            pytest.skip("integration test; set SPECINT_RUN_INTEGRATION=1 to run")
    else:
        disable_socket(allow_unix_socket=True)


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
