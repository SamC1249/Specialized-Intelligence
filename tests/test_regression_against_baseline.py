"""Regression guard against the June 2026 baseline.

Any change to fixtures or scorer must keep the aggregate ``__total__`` row
at least as good on the two headline metrics: number of license-clean
records and total license-clean duration. Individual per-source rows
may move (the scorer weights and metadata coverage change over time),
but the total supply must not fall.
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
from specint.sources.youtube import YouTubeCreativeCommonsSource

_BASELINE_PATH = Path(__file__).resolve().parents[1] / "reports" / "baseline-2026-06-20.json"


def _current_totals(fixtures_dir: Path):
    q = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    cc = CommonCrawlRecipeSource().parse(
        {
            "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        q,
    ) + CommonCrawlRecipeSource().parse(
        {
            "html": (fixtures_dir / "common_crawl/recipe_page_cc_by.html").read_text(),
            "url": "https://example.test/recipes/miso-sweet-potatoes",
        },
        q,
    )
    by = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), q
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), q
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), q
        ),
        "common_crawl": cc,
        "youtube_cc": YouTubeCreativeCommonsSource().parse(
            json.loads((fixtures_dir / "youtube/videos_cooking.json").read_text()), q
        ),
    }
    rows = run_comparison(q, by, notes="regression-guard")
    return next(r for r in rows if r.source == "__total__")


def test_totals_do_not_regress_against_june_baseline(fixtures_dir: Path):
    baseline = json.loads(_BASELINE_PATH.read_text())
    baseline_total = next(row for row in baseline["rows"] if row["source"] == "__total__")
    current = _current_totals(fixtures_dir)
    assert current.n_license_clean >= baseline_total["n_license_clean"], (
        f"license-clean supply regressed: {current.n_license_clean}"
        f" < {baseline_total['n_license_clean']}"
    )
    assert current.total_duration_s >= baseline_total["total_duration_s"], (
        f"license-clean duration regressed: {current.total_duration_s}"
        f" < {baseline_total['total_duration_s']}"
    )
