"""Cross-adapter invariants.

These tests exist to catch adapter bugs that per-adapter tests miss by
construction: shared schema violations, licence-contract violations
(e.g. a RESTRICTED record leaking a media_url), and provenance drift.

Each test loads the canonical fixture for every adapter, runs the pure
`parse()`, and asserts a global invariant.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.records import License, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _query():
    from specint.records import SourceQuery

    return SourceQuery(terms=["cooking", "recipe"], max_results=25)


def _wikimedia():
    return WikimediaCommonsSource().parse(
        json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), _query()
    )


def _archive_org():
    return ArchiveOrgSource().parse(
        json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), _query()
    )


def _peertube():
    return PeerTubeSource().parse(
        json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), _query()
    )


def _common_crawl():
    html = (FIXTURES / "common_crawl/recipe_page.html").read_text()
    return CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/garlic-butter-pasta"}, _query()
    )


_LOADERS = {
    "wikimedia": _wikimedia,
    "archive_org": _archive_org,
    "peertube": _peertube,
    "common_crawl": _common_crawl,
}


@pytest.mark.parametrize("slug", sorted(_LOADERS))
def test_parse_returns_list(slug: str):
    records = _LOADERS[slug]()
    assert isinstance(records, list), f"{slug}.parse() must return list, got {type(records)}"


@pytest.mark.parametrize("slug", sorted(_LOADERS))
def test_every_record_is_video_record(slug: str):
    for rec in _LOADERS[slug]():
        assert isinstance(rec, VideoRecord), f"{slug} emitted non-VideoRecord: {type(rec)}"


@pytest.mark.parametrize("slug", sorted(_LOADERS))
def test_license_contract(slug: str):
    """RESTRICTED records must never leak a media_url."""
    for rec in _LOADERS[slug]():
        if rec.license is License.RESTRICTED:
            assert rec.media_url is None, (
                f"{slug} record {rec.id} is RESTRICTED but exposes media_url={rec.media_url!r}"
            )
        if rec.media_url is not None:
            assert rec.license.is_redistributable, (
                f"{slug} record {rec.id} has media_url but license={rec.license.value} "
                "is not redistributable"
            )


@pytest.mark.parametrize("slug", sorted(_LOADERS))
def test_provenance_populated(slug: str):
    for rec in _LOADERS[slug]():
        assert rec.provenance is not None
        assert rec.provenance.extractor, f"{slug} record {rec.id} missing provenance.extractor"
        assert rec.provenance.extractor.startswith("specint."), (
            f"{slug} record {rec.id} has suspicious extractor={rec.provenance.extractor!r}"
        )
        assert rec.provenance.query, f"{slug} record {rec.id} missing provenance.query"


@pytest.mark.parametrize("slug", sorted(_LOADERS))
def test_id_shape(slug: str):
    for rec in _LOADERS[slug]():
        assert rec.id.startswith(f"{slug}:"), f"{slug} record id={rec.id!r} does not match slug"
        assert rec.source == slug, f"{slug} record source={rec.source!r} does not match slug"
        assert rec.source_native_id, f"{slug} record missing source_native_id"


def test_registry_lists_every_adapter_we_test():
    """If someone adds an adapter without a loader here, the contract
    suite would silently skip it. Fail fast instead."""
    assert set(REGISTRY) == set(_LOADERS), (
        "sources.REGISTRY and the contract loader map must stay in sync. "
        f"REGISTRY={sorted(REGISTRY)}, loaders={sorted(_LOADERS)}"
    )


def test_unknown_license_fraction_bounded():
    """Across all adapters, the fraction of UNKNOWN-licensed records on
    the fixture set must stay below 50%. A fresh regression here means
    somebody's license classifier broke."""
    total = 0
    unknown = 0
    for loader in _LOADERS.values():
        for rec in loader():
            total += 1
            if rec.license is License.UNKNOWN:
                unknown += 1
    assert total > 0
    assert unknown / total < 0.5, (
        f"too many UNKNOWN-license records in the fixture set: {unknown}/{total}"
    )
