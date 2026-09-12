"""Integration-marker scaffold.

These tests only run when `SPECINT_RUN_INTEGRATION=1` **and** the
matching credential is present. CI leaves the env unset so all tests
here are skipped, but running them locally with credentials verifies
that our adapters still parse live payloads.

Adding a new live smoke test: use the `integration` marker + an env
gate, keep assertions loose (only structural), and NEVER assert exact
counts, since upstream results are non-deterministic.
"""

from __future__ import annotations

import os

import pytest
from specint.records import SourceQuery
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCCSource

pytestmark = pytest.mark.integration

_LIVE = os.environ.get("SPECINT_RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not _LIVE, reason="integration disabled; set SPECINT_RUN_INTEGRATION=1")
def test_live_wikimedia_returns_video_records():
    src = WikimediaCommonsSource()
    records = list(src.search(SourceQuery(terms=["cooking"], max_results=3)))
    assert isinstance(records, list)
    for r in records:
        assert r.source == "wikimedia"
        assert r.url is not None


@pytest.mark.skipif(
    not _LIVE or not os.environ.get("YOUTUBE_API_KEY"),
    reason="YouTube integration disabled or YOUTUBE_API_KEY missing",
)
def test_live_youtube_cc_returns_metadata_only():
    src = YouTubeCCSource()
    records = list(src.search(SourceQuery(terms=["cooking tutorial"], max_results=3)))
    for r in records:
        assert r.media_url is None
