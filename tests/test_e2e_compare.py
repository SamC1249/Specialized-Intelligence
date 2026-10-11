"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.quality import dedupe
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.flickr import FlickrCCSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.vimeo import VimeoCCSource
from specint.sources.wikimedia import WikimediaCommonsSource

ALL_SOURCES = {"wikimedia", "archive_org", "peertube", "common_crawl", "vimeo", "flickr"}


def _load_all(fixtures_dir: Path, query: SourceQuery) -> dict[str, list]:
    return {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
        "vimeo": VimeoCCSource().parse(
            json.loads((fixtures_dir / "vimeo/search_cooking.json").read_text()), query
        ),
        "flickr": FlickrCCSource().parse(
            json.loads((fixtures_dir / "flickr/search_cooking.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all(fixtures_dir, query)

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == ALL_SOURCES | {"__total__"}

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    for row in rows:
        assert row.n_license_clean <= row.n_records

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == len(ALL_SOURCES) + 1


def test_e2e_dedup_never_increases_record_count(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all(fixtures_dir, query)
    pooled = [r for recs in by_source.values() for r in recs]
    deduped = dedupe(pooled)
    assert len(deduped) <= len(pooled)
    # No duplicate ids survive dedup.
    assert len({r.id for r in deduped}) == len(deduped)
