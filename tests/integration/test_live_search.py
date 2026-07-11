"""Integration test scaffold — gated behind SPECINT_RUN_INTEGRATION=1.

These hit real upstream services. They are intentionally *not* part of
the default suite so CI stays hermetic. Enable manually:

    SPECINT_RUN_INTEGRATION=1 pytest -m integration

Each test is defensive: it accepts an empty response and only asserts
structural invariants. Do not add fixtures here; unit tests already
own that path.
"""

from __future__ import annotations

import os

import pytest

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("SPECINT_RUN_INTEGRATION") != "1",
        reason="live network tests skipped unless SPECINT_RUN_INTEGRATION=1",
    ),
]


def _assert_records_are_well_formed(records):
    assert isinstance(records, list)
    for r in records:
        assert r.id.startswith(f"{r.source}:")
        assert str(r.url).startswith("http")
        if r.media_url is not None:
            assert r.license.is_redistributable, (
                f"media_url exposed for non-redistributable license: {r.license}"
            )
        assert r.license is not License.UNKNOWN or r.media_url is None


def test_wikimedia_live_search_returns_records():
    query = SourceQuery(terms=["pasta"], max_results=3)
    records = list(WikimediaCommonsSource().search(query))
    _assert_records_are_well_formed(records)


def test_archive_org_live_search_returns_records():
    query = SourceQuery(terms=["cooking"], max_results=3)
    records = list(ArchiveOrgSource().search(query))
    _assert_records_are_well_formed(records)


def test_peertube_live_search_returns_records():
    query = SourceQuery(terms=["cuisine"], max_results=3, languages=["fr"])
    records = list(PeerTubeSource().search(query))
    _assert_records_are_well_formed(records)
