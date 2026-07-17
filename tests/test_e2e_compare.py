"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_ablation, run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.openverse import OpenverseSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _build_by_source(fixtures_dir: Path, query: SourceQuery) -> dict:
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
        "openverse": OpenverseSource().parse(
            json.loads((fixtures_dir / "openverse/search_cooking.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    expected_sources = set(by_source.keys()) | {"__total__"}
    assert {row.source for row in rows} == expected_sources

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
    assert len(reloaded["rows"]) == len(by_source) + 1


def test_e2e_ablation_produces_ranking_per_config(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)

    result = run_ablation(query, by_source)

    assert "default" in result["configs"]
    assert result["sources"] == sorted(by_source.keys())

    for cfg in result["configs"]:
        ranking = result["rankings"][cfg]
        ranks = [row["rank"] for row in ranking]
        assert ranks == sorted(ranks)
        assert all(0.0 <= row["mean_quality"] <= 1.0 for row in ranking)

    for cfg, deltas in result["delta_vs_default"].items():
        assert cfg != "default"
        assert set(deltas.keys()) == set(result["sources"])
