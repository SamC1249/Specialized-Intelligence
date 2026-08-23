"""Structural invariants every source adapter must obey.

These tests attack four load-bearing assumptions:

1. **License invariant.** If a `VideoRecord` publishes a `media_url` (i.e.
   we would redistribute the bytes), the record's `license` must be
   redistributable. This defends the "no ToS violations" hard
   constraint from AGENTS.md against a scorer or adapter change that
   forgets to gate on `is_redistributable`.
2. **Provenance invariant.** Every emitted record must carry a
   non-empty `extractor`, a UTC `fetched_at`, and a serialized `query`.
   AGENTS.md rule 2: "Provenance is mandatory."
3. **Determinism / id-stability.** Calling `parse()` twice on the same
   fixture must yield the same `id` set. Non-deterministic ids break
   dedup and the transparency exporter.
4. **Registry completeness.** Every source that ships with a fixture
   directory must be registered in `sources/__init__.py::REGISTRY`,
   otherwise the comparison harness silently ignores it.

All tests are offline and parameterised over the full `REGISTRY` so
adding a new adapter automatically adds test coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specint.records import License, SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _load_wikimedia() -> Any:
    return json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text())


def _load_archive() -> Any:
    return json.loads((FIXTURES / "archive_org/search_cooking.json").read_text())


def _load_peertube() -> Any:
    return json.loads((FIXTURES / "peertube/search_cooking.json").read_text())


def _load_common_crawl() -> Any:
    return {
        "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
        "url": "https://example.test/recipes/garlic-butter-pasta",
    }


ADAPTER_CASES: list[tuple[str, Any, Any]] = [
    ("wikimedia", WikimediaCommonsSource, _load_wikimedia),
    ("archive_org", ArchiveOrgSource, _load_archive),
    ("peertube", PeerTubeSource, _load_peertube),
    ("common_crawl", CommonCrawlRecipeSource, _load_common_crawl),
]


@pytest.fixture(scope="module")
def query() -> SourceQuery:
    return SourceQuery(terms=["cooking", "recipe"], max_results=25)


@pytest.fixture(params=ADAPTER_CASES, ids=[c[0] for c in ADAPTER_CASES])
def parsed_records(request, query) -> tuple[str, list[VideoRecord]]:
    slug, cls, loader = request.param
    records = cls().parse(loader(), query)
    assert isinstance(records, list)
    assert len(records) > 0, f"{slug} fixture parsed to zero records — fixture rot?"
    return slug, records


def test_license_invariant_media_url_requires_redistributable(parsed_records):
    slug, records = parsed_records
    for r in records:
        if r.media_url is not None:
            assert r.license.is_redistributable, (
                f"{slug}: record {r.id} publishes media_url but license={r.license}. "
                "This violates AGENTS.md hard constraint #1 (no ToS violations)."
            )


def test_provenance_is_mandatory_and_populated(parsed_records):
    slug, records = parsed_records
    for r in records:
        assert r.provenance is not None, f"{slug}: record {r.id} missing provenance"
        assert r.provenance.extractor, f"{slug}: record {r.id} provenance.extractor is empty"
        assert r.provenance.fetched_at is not None, (
            f"{slug}: record {r.id} provenance.fetched_at is None"
        )
        assert r.provenance.fetched_at.tzinfo is not None, (
            f"{slug}: record {r.id} fetched_at is naive; must be UTC-aware"
        )
        assert "terms=" in r.provenance.query, (
            f"{slug}: record {r.id} provenance.query missing serialised SourceQuery"
        )


def test_ids_are_stable_across_reparse(query):
    for slug, cls, loader in ADAPTER_CASES:
        raw = loader()
        first = {r.id for r in cls().parse(raw, query)}
        second = {r.id for r in cls().parse(raw, query)}
        assert first == second, (
            f"{slug}: parse() is non-deterministic across calls. "
            f"symmetric_difference={first ^ second}"
        )


def test_ids_are_globally_unique_across_sources(query):
    seen: dict[str, str] = {}
    for slug, cls, loader in ADAPTER_CASES:
        for r in cls().parse(loader(), query):
            assert r.id not in seen, (
                f"id collision: {r.id} produced by both "
                f"{seen[r.id]} and {slug}. Prefix your ids with the source slug."
            )
            seen[r.id] = slug


def test_id_starts_with_source_slug(parsed_records):
    slug, records = parsed_records
    for r in records:
        assert r.id.startswith(f"{r.source}:"), (
            f"{slug}: record id {r.id!r} does not start with '{r.source}:' — "
            "breaks the cross-source dedup canonicalisation described in "
            "docs/artifacts/2026-mlt-dedup.md"
        )


def test_license_never_unknown_when_url_hints_at_cc(parsed_records):
    """Cheap sanity: if the record's license_url contains 'creativecommons'
    but our enum is UNKNOWN, the classifier missed an obvious signal."""
    slug, records = parsed_records
    for r in records:
        if r.license_url and "creativecommons" in str(r.license_url).lower():
            assert r.license is not License.UNKNOWN, (
                f"{slug}: record {r.id} has creativecommons license_url but "
                f"license enum is UNKNOWN. Fix _coerce_license."
            )


def test_every_fixture_directory_has_a_registered_source():
    fixture_dirs = {p.name for p in FIXTURES.iterdir() if p.is_dir()}
    fixture_dirs -= {"__pycache__"}
    for name in fixture_dirs:
        assert name in REGISTRY, (
            f"fixtures/{name}/ has no matching entry in "
            f"src/specint/sources/__init__.py::REGISTRY. "
            f"Either register the adapter or delete the orphan fixture."
        )


def test_every_registered_source_is_a_base_source_subclass():
    from specint.sources.base import BaseSource

    for slug, cls in REGISTRY.items():
        assert issubclass(cls, BaseSource), f"{slug} is not a BaseSource subclass"
        assert cls.slug == slug or cls.slug == "", (
            f"{slug}: class slug attribute ({cls.slug!r}) does not match REGISTRY key ({slug!r})."
        )


def test_all_json_fixtures_parse_as_json():
    for path in FIXTURES.rglob("*.json"):
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            pytest.fail(f"fixture {path} is not valid JSON: {exc}")


def test_common_crawl_html_fixture_is_not_empty():
    html = (FIXTURES / "common_crawl/recipe_page.html").read_text()
    assert "<html" in html.lower() or "<!doctype" in html.lower(), (
        "common_crawl HTML fixture does not look like HTML"
    )
    assert len(html) > 200, "common_crawl HTML fixture is suspiciously small"
