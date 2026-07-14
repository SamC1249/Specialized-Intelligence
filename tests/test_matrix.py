"""End-to-end multi-query matrix harness tests."""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare.harness import run_matrix
from specint.records import SourceQuery, SourceQuerySuite
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _build_by_source_fn(fixtures_dir: Path):
    def loader(query: SourceQuery) -> dict[str, list]:
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
        }

    return loader


def test_run_matrix_shape_and_dedup(fixtures_dir: Path):
    suite = SourceQuerySuite.model_validate(
        json.loads((fixtures_dir / "suite/query_suite.json").read_text())
    )
    result = run_matrix(suite, _build_by_source_fn(fixtures_dir), scorer="v1", dedup=True)

    assert set(result) == {"per_query", "per_source"}
    per_query = result["per_query"]
    per_source = result["per_source"]

    n_queries = len(suite.queries)
    n_sources = 4
    assert len(per_query) == n_queries * (n_sources + 1)
    assert {r.source for r in per_source} == {
        "wikimedia",
        "archive_org",
        "peertube",
        "common_crawl",
        "__total__",
    }

    total_row = next(r for r in per_source if r.source == "__total__")
    per_source_records = sum(r.n_records for r in per_source if r.source != "__total__")
    assert total_row.n_records + total_row.n_duplicates == per_source_records


def test_run_matrix_scorer_switch(fixtures_dir: Path):
    suite = SourceQuerySuite.model_validate(
        json.loads((fixtures_dir / "suite/query_suite.json").read_text())
    )
    r_v1 = run_matrix(suite, _build_by_source_fn(fixtures_dir), scorer="v1")
    r_v2 = run_matrix(suite, _build_by_source_fn(fixtures_dir), scorer="v2")
    v1_total = next(r for r in r_v1["per_source"] if r.source == "__total__")
    v2_total = next(r for r in r_v2["per_source"] if r.source == "__total__")
    assert v1_total.scorer == "v1"
    assert v2_total.scorer == "v2"
    assert v1_total.n_records == v2_total.n_records
    assert v1_total.n_license_clean == v2_total.n_license_clean
