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
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCreativeCommonsSource


def _load_all_sources(fixtures_dir: Path, query: SourceQuery) -> dict:
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
        "youtube_cc": YouTubeCreativeCommonsSource().parse(
            json.loads((fixtures_dir / "youtube_cc/search_cc_recipe.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all_sources(fixtures_dir, query)

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {
        "wikimedia",
        "archive_org",
        "peertube",
        "common_crawl",
        "youtube_cc",
        "__total__",
    }

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    # License-clean count must be monotonically <= n_records.
    for row in rows:
        assert row.n_license_clean <= row.n_records

    # Dedup delta is well-formed even when nothing collapses.
    assert 0 < total.n_after_dedup <= total.n_records

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == 6


def test_e2e_dedup_collapses_synthetic_duplicates(fixtures_dir: Path):
    """When a source re-hosts the same title+duration, the __total__ row
    reports fewer records after dedup than before."""
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_source = _load_all_sources(fixtures_dir, query)

    wm = by_source["wikimedia"][0]
    mirror = wm.model_copy(update={"id": "archive_org:mirror", "source": "archive_org"})
    by_source["archive_org"] = [*by_source["archive_org"], mirror]

    with_dedup = run_comparison(query, by_source, notes="dedup", dedup=True)
    without = run_comparison(query, by_source, notes="raw", dedup=False)
    total_dedup = next(r for r in with_dedup if r.source == "__total__")
    total_raw = next(r for r in without if r.source == "__total__")
    assert total_raw.n_after_dedup == total_raw.n_records
    assert total_dedup.n_after_dedup < total_dedup.n_records
