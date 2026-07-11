"""Tests for scorer-aware harness paths (`head_to_head`, `run_comparison`)."""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import head_to_head, run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _by_source(fixtures_dir: Path, query: SourceQuery):
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


def test_head_to_head_returns_row_set_per_scorer(fixtures_dir):
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_src = _by_source(fixtures_dir, query)
    out = head_to_head(query, by_src, scorers=("v1", "v2"))
    assert set(out) == {"v1", "v2"}
    for rows in out.values():
        sources = {r.source for r in rows}
        assert "__total__" in sources
        for row in rows:
            assert row.n_license_clean <= row.n_records
            assert 0.0 <= row.mean_quality <= 1.0


def test_v2_changes_at_least_one_source_rank(fixtures_dir):
    """H2 falsifiable check: v2 must change the pipeline in a measurable way.

    We don't require a specific new ordering, only that v2 is not a no-op
    on the seed fixtures — otherwise the added complexity has no return.
    """
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_src = _by_source(fixtures_dir, query)
    v1_rows = run_comparison(query, by_src, scorer="v1")
    v2_rows = run_comparison(query, by_src, scorer="v2")

    def _rank(rows):
        per_src = [r for r in rows if r.source != "__total__"]
        return [r.source for r in sorted(per_src, key=lambda r: -r.mean_quality)]

    v1_scores = {r.source: r.mean_quality for r in v1_rows if r.source != "__total__"}
    v2_scores = {r.source: r.mean_quality for r in v2_rows if r.source != "__total__"}
    assert v1_scores != v2_scores, "v2 scorer produces identical means to v1"
    _ = _rank(v1_rows), _rank(v2_rows)


def test_v2_lifts_archive_org_over_v1(fixtures_dir):
    """H2 sub-claim: neutral-unknown metadata handling should raise
    archive_org's mean quality relative to v1 (where missing width/height
    were scored as zero).
    """
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_src = _by_source(fixtures_dir, query)
    v1 = {r.source: r.mean_quality for r in run_comparison(query, by_src, scorer="v1")}
    v2 = {r.source: r.mean_quality for r in run_comparison(query, by_src, scorer="v2")}
    assert v2["archive_org"] > v1["archive_org"], (v1, v2)
