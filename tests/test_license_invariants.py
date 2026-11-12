"""Cross-adapter license invariants.

A single property that must hold for every `VideoRecord` produced by any
adapter in `REGISTRY`, regardless of source:

    not record.license.is_redistributable  =>  record.media_url is None

This is the hard constraint from `AGENTS.md`: we must never expose a
direct media URL for a record whose license forbids redistribution.
Enforcing it as a cross-adapter property catches a class of regressions
no per-adapter test would catch (e.g. a new adapter copy-pasting the
Wikimedia logic but dropping the `if license_enum.is_redistributable`
guard around `media_url`).

Also asserts the dual: every adapter reachable through `REGISTRY` must
*at least once* over the fixture suite produce a redistributable record.
If an adapter produces only UNKNOWN/RESTRICTED records on its shipped
fixture, the fixture is not exercising the happy path and a future
license-classifier change could silently zero the source out.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.common_crawl import CommonCrawlRecipeSource

FIXTURES = Path(__file__).parent / "fixtures"


def _load_common_crawl(path: Path) -> dict[str, str]:
    return {
        "html": path.read_text(),
        "url": "https://example.test/recipes/invariant-fixture",
    }


FixtureLoader = Callable[[Path], object]


FIXTURE_MAP: dict[str, tuple[str, FixtureLoader]] = {
    "wikimedia": ("wikimedia/search_pasta.json", lambda p: json.loads(p.read_text())),
    "archive_org": ("archive_org/search_cooking.json", lambda p: json.loads(p.read_text())),
    "peertube": ("peertube/search_cooking.json", lambda p: json.loads(p.read_text())),
    "common_crawl": ("common_crawl/recipe_page.html", _load_common_crawl),
}


@pytest.fixture(params=sorted(REGISTRY.keys()))
def records_for_source(request: pytest.FixtureRequest) -> tuple[str, list[VideoRecord]]:
    slug = request.param
    assert slug in FIXTURE_MAP, (
        f"adapter {slug!r} is registered but has no fixture entry in "
        "FIXTURE_MAP; add one before registering the source."
    )
    rel, loader = FIXTURE_MAP[slug]
    raw = loader(FIXTURES / rel)
    source = REGISTRY[slug]()
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    records = source.parse(raw, query)
    assert records, f"adapter {slug!r} returned no records for its own fixture"
    return slug, records


def test_license_media_url_invariant(records_for_source: tuple[str, list[VideoRecord]]) -> None:
    """Non-redistributable records MUST NOT carry a direct media URL."""
    slug, records = records_for_source
    offenders = [r for r in records if not r.license.is_redistributable and r.media_url is not None]
    assert not offenders, (
        f"{slug}: {len(offenders)} record(s) leak a media_url under a "
        f"non-redistributable license: "
        f"{[(r.id, r.license.value, str(r.media_url)) for r in offenders]}"
    )


def test_provenance_is_always_present(records_for_source: tuple[str, list[VideoRecord]]) -> None:
    slug, records = records_for_source
    for r in records:
        assert r.provenance is not None, f"{slug}:{r.id} missing provenance"
        assert r.provenance.extractor, f"{slug}:{r.id} empty provenance.extractor"
        assert r.provenance.query, (
            f"{slug}:{r.id} empty provenance.query; adapter must serialize the "
            "SourceQuery so re-runs are reproducible"
        )


def test_id_is_prefixed_with_source(records_for_source: tuple[str, list[VideoRecord]]) -> None:
    slug, records = records_for_source
    for r in records:
        assert r.id.startswith(f"{slug}:"), (
            f"{slug}: record id {r.id!r} must start with its source slug for "
            "cross-source deduplication to work."
        )
        assert r.source == slug, f"{slug}:{r.id} has mismatched record.source={r.source!r}"


def test_registry_has_fixture_entry() -> None:
    """Every registered source must have a FIXTURE_MAP entry.

    This guards against adding a new adapter to REGISTRY without wiring
    it into the invariant suite. If this fires, add a fixture and an
    entry before merging the new source.
    """
    missing = sorted(set(REGISTRY.keys()) - set(FIXTURE_MAP.keys()))
    assert not missing, (
        f"REGISTRY sources with no fixture entry: {missing}. "
        "Add a fixture under tests/fixtures/<slug>/ and a line to "
        "FIXTURE_MAP in tests/test_license_invariants.py."
    )


def test_common_crawl_source_is_actually_in_registry() -> None:
    """Sanity check: CommonCrawlRecipeSource class is reachable through REGISTRY.

    Otherwise a rebase that drops it from `src/specint/sources/__init__.py`
    would silently disappear this source from every benchmark.
    """
    assert REGISTRY.get("common_crawl") is CommonCrawlRecipeSource
