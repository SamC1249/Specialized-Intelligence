"""Guardrail: `parse()` must be pure and never open a socket.

The AGENTS.md "Reproducible offline tests" hard-constraint depends on
adapters being splittable into a pure `parse` half and a network-side
`search` half. This test enforces the pure-half promise for every
registered source by monkey-patching `socket.socket` to raise for the
duration of the fixture-driven e2e compare.

If a future adapter accidentally puts a `httpx.get(...)` inside its
`parse` (or in a helper that `parse` calls transitively), this test will
detect it before it ships.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


class _NoNetworkError(RuntimeError):
    """Raised when a supposedly-offline codepath opens a socket."""


@pytest.fixture
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    real_socket = socket.socket

    def _blocked(*args: Any, **kwargs: Any) -> socket.socket:
        raise _NoNetworkError(
            "socket.socket() was called during an offline test — "
            "an adapter's parse() is doing network I/O it must not."
        )

    monkeypatch.setattr(socket, "socket", _blocked)
    try:
        yield
    finally:
        monkeypatch.setattr(socket, "socket", real_socket)


def test_parse_never_opens_socket(fixtures_dir: Path, _no_network: None) -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)

    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()),
            query,
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()),
            query,
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()),
            query,
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }

    rows = run_comparison(query, by_source, notes="offline-contract")
    assert any(row.source == "__total__" and row.n_records > 0 for row in rows)


def test_blocked_socket_actually_blocks(_no_network: None) -> None:
    """Sanity check: the guard fixture must actually raise on socket use."""
    with pytest.raises(_NoNetworkError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
