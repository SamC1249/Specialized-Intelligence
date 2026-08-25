from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class LiveNetworkBlockedError(RuntimeError):
    """Raised when a unit test tries to hit the real network.

    AGENTS.md rule #4: "Reproducible offline tests. CI must pass
    without network. Use fixtures in ``tests/fixtures/``, never live
    HTTP in unit tests." This guard converts a policy into a hard
    invariant: any outbound ``httpx.Client.send`` in a test that is
    not marked ``@pytest.mark.integration`` raises immediately.
    """


@pytest.fixture(autouse=True)
def _block_live_network(request, monkeypatch):
    """Autouse guard. Integration-marked tests opt out explicitly."""
    if request.node.get_closest_marker("integration"):
        yield
        return

    def _refuse_send(self, request, *args, **kwargs):
        raise LiveNetworkBlockedError(
            f"Blocked outbound HTTP {request.method} {request.url}. "
            "Unit tests must be offline (AGENTS.md rule #4). "
            "Use a fixture or mark the test @pytest.mark.integration."
        )

    monkeypatch.setattr(httpx.Client, "send", _refuse_send)
    monkeypatch.setattr(httpx.AsyncClient, "send", _refuse_send)
    yield


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
