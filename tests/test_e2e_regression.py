"""Regression guard against silent baseline drift.

The seed commit committed `reports/baseline-2026-06-20.json`. The intent of
this file was to be the *reference ranking* of sources on the checked-in
fixtures. Without an explicit test, any adapter change can silently
reshuffle that ranking — see `docs/plan-2026-08-13.md` § H1.

This test replays the exact same input the seed commit used (`terms=cooking
recipe`, fixture directory) and asserts:

  1. All four seed sources still appear in the report.
  2. Their `mean_quality` ordering matches the baseline ordering.
  3. The aggregate `n_records == sum(per-source n_records)`.

If a legitimate adapter improvement should shift the ranking, the test
should be updated with a *new* baseline in the same PR, with a note in
`plan.md` explaining why. That is the desired workflow — the friction is
intentional.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "reports" / "baseline-2026-06-20.json"


def _baseline_source_ordering() -> list[str]:
    payload = json.loads(BASELINE_PATH.read_text())
    per_source = [row for row in payload["rows"] if row["source"] != "__total__"]
    per_source.sort(key=lambda r: (-r["mean_quality"], r["source"]))
    return [row["source"] for row in per_source]


def test_baseline_report_still_exists_and_is_valid_json():
    payload = json.loads(BASELINE_PATH.read_text())
    assert "rows" in payload and "query" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert {"wikimedia", "archive_org", "peertube", "common_crawl", "__total__"} <= sources


def test_source_ranking_matches_baseline(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = {
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

    rows = run_comparison(query, by_source, notes="regression")
    per_source = [r for r in rows if r.source != "__total__"]
    per_source.sort(key=lambda r: (-r.mean_quality, r.source))
    actual_ordering = [r.source for r in per_source]

    assert actual_ordering == _baseline_source_ordering()

    total = next(r for r in rows if r.source == "__total__")
    assert total.n_records == sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_after_dedup <= total.n_records


def test_dedup_column_is_populated(fixtures_dir: Path):
    """`n_after_dedup` must be > 0 for every non-empty source."""
    query = SourceQuery(terms=["cooking"], max_results=25)
    records = WikimediaCommonsSource().parse(
        json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
    )
    rows = run_comparison(query, {"wikimedia": records})
    non_total = [r for r in rows if r.source != "__total__"]
    assert non_total
    for row in non_total:
        assert 0 < row.n_after_dedup <= row.n_records
