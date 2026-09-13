"""Unit tests for the policy sweep harness."""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare.sweep import _pareto_frontier, run_sweep
from specint.quality import POLICIES
from specint.records import BenchmarkResult, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _bench(source: str, mean: float, clean: int) -> BenchmarkResult:
    return BenchmarkResult(
        source=source,
        query_terms=["x"],
        n_records=1,
        n_license_clean=clean,
        total_duration_s=0.0,
        mean_quality=mean,
        p50_quality=mean,
        p90_quality=mean,
        unique_authors=0,
        notes="",
    )


class TestParetoFrontier:
    def test_dominated_row_removed(self):
        a = _bench("a", mean=0.8, clean=5)
        b = _bench("b", mean=0.6, clean=3)
        frontier = _pareto_frontier([a, b])
        assert a in frontier and b not in frontier

    def test_two_non_dominated_rows_kept(self):
        a = _bench("a", mean=0.8, clean=1)
        b = _bench("b", mean=0.6, clean=5)
        frontier = _pareto_frontier([a, b])
        assert a in frontier and b in frontier
        assert len(frontier) == 2

    def test_ties_kept(self):
        a = _bench("a", mean=0.8, clean=5)
        b = _bench("b", mean=0.8, clean=5)
        frontier = _pareto_frontier([a, b])
        assert a in frontier and b in frontier
        assert len(frontier) == 2


class TestRunSweepAgainstFixtures:
    def _by_source(self, fixtures_dir: Path, query: SourceQuery) -> dict[str, list]:
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

    def test_structure(self, fixtures_dir: Path):
        query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
        by_source = self._by_source(fixtures_dir, query)
        payload = run_sweep(query, by_source, notes="test")

        assert set(payload) == {
            "meta",
            "policies",
            "rows",
            "frontier",
            "dedup",
            "policy_quality_p50",
        }
        assert sorted(payload["policies"]) == sorted(POLICIES)

        totals = [r for r in payload["rows"] if r["source"] == "__total__"]
        assert len(totals) == len(POLICIES)
        assert len({t["policy"] for t in totals}) == len(POLICIES)

        # Every row must serialise cleanly.
        assert json.dumps(payload, sort_keys=True)

    def test_frontier_is_subset_of_totals(self, fixtures_dir: Path):
        query = SourceQuery(terms=["cooking"], max_results=25)
        payload = run_sweep(query, self._by_source(fixtures_dir, query))
        total_keys = {
            (r["policy"], r["mean_quality"]) for r in payload["rows"] if r["source"] == "__total__"
        }
        for row in payload["frontier"]:
            assert (row["policy"], row["mean_quality"]) in total_keys

    def test_dedup_report_shape(self, fixtures_dir: Path):
        query = SourceQuery(terms=["cooking"], max_results=25)
        payload = run_sweep(query, self._by_source(fixtures_dir, query))
        dedup = payload["dedup"]
        assert dedup["n_records_in"] >= 1
        assert dedup["n_records_out"] <= dedup["n_records_in"]
        assert dedup["n_duplicates_collapsed"] == (dedup["n_records_in"] - dedup["n_records_out"])
