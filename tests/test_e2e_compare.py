"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import compare_runs, run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikidata import WikidataSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _by_source(fixtures_dir: Path, query: SourceQuery) -> dict[str, list]:
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
        "wikidata": WikidataSource().parse(
            json.loads((fixtures_dir / "wikidata/sparql_cooking.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _by_source(fixtures_dir, query)

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {
        "wikimedia",
        "archive_org",
        "peertube",
        "common_crawl",
        "wikidata",
        "__total__",
    }

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    # License-clean count must be monotonically <= n_records.
    for row in rows:
        assert row.n_license_clean <= row.n_records
        assert 0.0 <= row.license_clean_ratio <= 1.0
        assert row.n_unique_after_dedup <= row.n_records
        assert row.scorer_profile == "v1"

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == 6


def test_e2e_v2_profile_does_not_regress_mean_quality(fixtures_dir: Path):
    """The procedural-aware profile should not Pareto-be-dominated by v1 on fixtures."""
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _by_source(fixtures_dir, query)

    v1_rows = run_comparison(query, by_source, notes="v1", scorer_profile="v1")
    v2_rows = run_comparison(query, by_source, notes="v2", scorer_profile="v2_procedural")
    delta = compare_runs(v1_rows, v2_rows)
    assert delta.verdict != "dominated"
