"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added, and covers both scorers plus the dedup path.
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
from specint.sources.youtube_cc import YouTubeCCSource

EXPECTED_SOURCES = {
    "wikimedia",
    "archive_org",
    "peertube",
    "common_crawl",
    "youtube_cc",
    "__total__",
}


def _build_by_source(fixtures_dir: Path, query: SourceQuery) -> dict[str, list]:
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
        "youtube_cc": YouTubeCCSource().parse(
            json.loads((fixtures_dir / "youtube_cc/search_cooking.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_v1(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)
    rows = run_comparison(query, by_source, notes="e2e-fixture", scorer="v1")

    sources_seen = {row.source for row in rows}
    assert sources_seen == EXPECTED_SOURCES

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    for row in rows:
        assert row.n_license_clean <= row.n_records
        assert row.scorer == "v1"
        assert row.n_duplicates_removed == 0

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == len(EXPECTED_SOURCES)


def test_e2e_offline_compare_v2_differs_from_v1(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)

    v1 = run_comparison(query, by_source, scorer="v1")
    v2 = run_comparison(query, by_source, scorer="v2")

    v1_total = next(r for r in v1 if r.source == "__total__")
    v2_total = next(r for r in v2 if r.source == "__total__")

    assert v1_total.n_records == v2_total.n_records
    assert v1_total.scorer == "v1"
    assert v2_total.scorer == "v2"
    assert v1_total.mean_quality != v2_total.mean_quality


def test_e2e_offline_compare_with_dedup(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)
    rows = run_comparison(query, by_source, scorer="v2", dedup=True)
    total = next(r for r in rows if r.source == "__total__")
    assert total.n_duplicates_removed >= 0
    per_source_records = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_records
