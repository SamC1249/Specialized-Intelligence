"""Baseline-regression ratchet.

Reproduces the fixture-driven benchmark and asserts that per-source
`mean_quality` stays within a small tolerance of the checked-in
`reports/baseline-2026-06-20.json`. This is a *ratchet*: a change that
legitimately improves quality must land in the same PR as an update to
this baseline file (see `docs/plan-2026-07-16.md` for the update
protocol).

The comparison is intentionally loose (±0.02) so tiny numerical drift
from library upgrades does not paper-cut the pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
BASELINE_PATH = REPO_ROOT / "reports" / "baseline-2026-06-20.json"

TOLERANCE = 0.02


def _rebuild_by_source(query: SourceQuery) -> dict[str, list]:
    return {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }


@pytest.fixture(scope="module")
def baseline_rows() -> dict[str, dict]:
    payload = json.loads(BASELINE_PATH.read_text())
    return {row["source"]: row for row in payload["rows"]}


@pytest.fixture(scope="module")
def current_rows() -> dict[str, dict]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, _rebuild_by_source(query), notes="fixture-baseline")
    return {r.source: r.model_dump(mode="json") for r in rows}


@pytest.mark.parametrize(
    "source", ["wikimedia", "archive_org", "peertube", "common_crawl", "__total__"]
)
def test_mean_quality_within_tolerance(
    baseline_rows: dict[str, dict], current_rows: dict[str, dict], source: str
) -> None:
    b = baseline_rows[source]
    c = current_rows[source]
    delta = c["mean_quality"] - b["mean_quality"]
    assert abs(delta) <= TOLERANCE, (
        f"mean_quality for {source} drifted by {delta:+.4f} "
        f"(baseline {b['mean_quality']:.4f}, current {c['mean_quality']:.4f}). "
        f"If this is an improvement, regenerate reports/baseline-2026-06-20.json "
        f"in the same PR and note the delta in plan.md."
    )


@pytest.mark.parametrize(
    "source", ["wikimedia", "archive_org", "peertube", "common_crawl", "__total__"]
)
def test_n_records_non_regressive(
    baseline_rows: dict[str, dict], current_rows: dict[str, dict], source: str
) -> None:
    b = baseline_rows[source]
    c = current_rows[source]
    assert c["n_records"] >= b["n_records"], (
        f"n_records for {source} dropped from {b['n_records']} to {c['n_records']}; "
        "the ratchet only allows growth in record count without a plan-level justification."
    )
