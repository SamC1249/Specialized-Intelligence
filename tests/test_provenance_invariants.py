"""Invariant: every parsed VideoRecord carries meaningful provenance.

AGENTS.md, hard constraint #2: "Provenance is mandatory. Every record
must carry source URL, license, capture timestamp, and the exact
extractor commit hash." This test enforces the *shape* of that
contract across every registered adapter, running against the
checked-in fixtures.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _parse_all() -> list[tuple[str, VideoRecord]]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    out: list[tuple[str, VideoRecord]] = []

    wikimedia = WikimediaCommonsSource().parse(
        json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
    )
    out.extend(("wikimedia", r) for r in wikimedia)

    archive = ArchiveOrgSource().parse(
        json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), query
    )
    out.extend(("archive_org", r) for r in archive)

    peertube = PeerTubeSource().parse(
        json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), query
    )
    out.extend(("peertube", r) for r in peertube)

    common_crawl = CommonCrawlRecipeSource().parse(
        {
            "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        query,
    )
    out.extend(("common_crawl", r) for r in common_crawl)
    return out


ALL_RECORDS = _parse_all()


def test_at_least_one_record_per_source() -> None:
    seen = {slug for slug, _ in ALL_RECORDS}
    assert seen == set(REGISTRY.keys()), (
        f"missing coverage for sources: {set(REGISTRY.keys()) - seen}"
    )


@pytest.mark.parametrize(
    ("source", "record"),
    ALL_RECORDS,
    ids=[f"{slug}:{r.source_native_id}" for slug, r in ALL_RECORDS],
)
def test_provenance_shape(source: str, record: VideoRecord) -> None:
    prov = record.provenance
    assert prov.extractor, "extractor module path must be set"
    assert prov.extractor.startswith("specint.sources."), (
        f"extractor {prov.extractor!r} must point at an adapter module"
    )
    assert source in prov.extractor, (
        f"extractor {prov.extractor!r} does not match source slug {source!r}"
    )
    assert prov.extractor_git, "extractor_git must be set (default 'dev' is fine)"
    assert isinstance(prov.fetched_at, datetime), "fetched_at must be a datetime"
    assert prov.fetched_at.tzinfo is not None, "fetched_at must be timezone-aware"
    assert prov.fetched_at <= datetime.now(UTC), "fetched_at must not be in the future"
    assert prov.query, "query serialization must be non-empty"


@pytest.mark.parametrize(
    ("source", "record"),
    ALL_RECORDS,
    ids=[f"{slug}:{r.source_native_id}" for slug, r in ALL_RECORDS],
)
def test_identity_shape(source: str, record: VideoRecord) -> None:
    assert record.source == source
    assert record.id.startswith(f"{source}:"), (
        f"id {record.id!r} does not start with source slug {source!r}:"
    )
    assert record.source_native_id, "source_native_id must be non-empty"
    assert str(record.url).startswith(("http://", "https://"))


def test_media_url_only_when_license_permits() -> None:
    """media_url may be set only for a redistributable license."""
    for _, record in ALL_RECORDS:
        if record.media_url is not None:
            assert record.license.is_redistributable, (
                f"record {record.id} exposes media_url but license "
                f"{record.license} is not redistributable"
            )
