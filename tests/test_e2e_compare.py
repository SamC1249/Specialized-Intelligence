"""End-to-end test: run the full comparison harness against fixtures.

Intentionally network-free. Each adapter's `parse` is invoked against a
checked-in fixture and the harness aggregates the results. Also
enforces a regression guard: the aggregate mean_quality on the same
fixtures must be at least as good as the committed baseline (minus a
tiny slack). This is how the "comparison-first rule" bites in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison, run_full_report
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube import YouTubeCCSource

BASELINE_MEAN = 0.4991463541666667  # __total__ from reports/baseline-2026-06-20.json
BASELINE_SLACK = 0.05
REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_all_by_source(fixtures_dir: Path, query: SourceQuery):
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
        "youtube": YouTubeCCSource().parse(
            json.loads((fixtures_dir / "youtube/videos_list.json").read_text()), query
        ),
    }


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all_by_source(fixtures_dir, query)
    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {
        "wikimedia",
        "archive_org",
        "peertube",
        "common_crawl",
        "youtube",
        "__total__",
    }

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
    assert len(reloaded["rows"]) == 6


def test_e2e_dedupe_report_included(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all_by_source(fixtures_dir, query)
    payload = run_full_report(query, by_source, notes="e2e-fixture", with_dedupe=True)
    assert "dedupe" in payload
    assert payload["dedupe"]["n_records"] >= payload["dedupe"]["n_after_dedupe"]
    assert isinstance(payload["dedupe"]["overlap"], dict)


def test_regression_guard_beats_baseline(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_all_by_source(fixtures_dir, query)
    rows = run_comparison(query, by_source, notes="regression-guard")
    total = next(r for r in rows if r.source == "__total__")
    assert total.mean_quality >= BASELINE_MEAN - BASELINE_SLACK, (
        f"Aggregate mean_quality {total.mean_quality:.3f} regressed from"
        f" baseline {BASELINE_MEAN:.3f} (slack {BASELINE_SLACK})."
    )
