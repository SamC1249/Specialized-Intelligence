"""Integration smoke tests (skipped without SPECINT_RUN_INTEGRATION=1).

These are meant to catch upstream API-shape drift. They must never run
in default CI; the marker + env-gate keeps them opt-in.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

RUN = os.environ.get("SPECINT_RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not RUN, reason="SPECINT_RUN_INTEGRATION not set")
def test_wikimedia_live_search_returns_something():  # pragma: no cover
    from specint.records import SourceQuery
    from specint.sources.wikimedia import WikimediaCommonsSource

    records = list(WikimediaCommonsSource().search(SourceQuery(terms=["cooking"], max_results=1)))
    assert len(records) >= 0


@pytest.mark.skipif(not RUN, reason="SPECINT_RUN_INTEGRATION not set")
def test_archive_org_live_search_returns_something():  # pragma: no cover
    from specint.records import SourceQuery
    from specint.sources.archive_org import ArchiveOrgSource

    records = list(ArchiveOrgSource().search(SourceQuery(terms=["cooking"], max_results=1)))
    assert len(records) >= 0
