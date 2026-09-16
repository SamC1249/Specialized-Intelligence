"""Tests for `specint.fixtures.load_all_fixtures`.

Guards against silent regressions where a manifest entry loses its
fixture file. Every registered adapter must return at least one record
from its fixtures.
"""

from __future__ import annotations

from specint.fixtures import FIXTURE_MANIFEST, load_all_fixtures
from specint.records import SourceQuery
from specint.sources import REGISTRY


def test_fixture_manifest_covers_all_registered_sources():
    assert set(FIXTURE_MANIFEST) == set(REGISTRY)


def test_all_fixture_sources_yield_records():
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_all_fixtures(query)
    assert set(by_source) == set(REGISTRY)
    for slug, records in by_source.items():
        assert records, f"expected fixture records for {slug}"


def test_multilingual_records_present():
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_all_fixtures(query)
    wm_titles = " ".join(r.title for r in by_source["wikimedia"])
    pt_titles = " ".join(r.title for r in by_source["peertube"])
    assert any(ch.isascii() is False for ch in wm_titles + pt_titles), (
        "expected at least one non-ASCII (multilingual) title in fixtures"
    )
