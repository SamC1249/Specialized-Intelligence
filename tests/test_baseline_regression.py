"""Baseline regression test — locks in the comparison-first rule.

`AGENTS.md` requires that new sources or filters ship with a benchmark
entry, but nothing today prevents `Coding-Agent` from silently
regressing the previous baseline. This test:

1. Reads the frozen `reports/baseline-2026-06-20.json`.
2. Reruns the comparison harness against the *same* fixtures.
3. Asserts each per-source `mean_quality` stays inside a
   `[baseline - MAX_REGRESSION, baseline + MAX_IMPROVEMENT]` band.
   - A regression >0.05 fails loudly.
   - An unexplained *improvement* >0.30 also fails: usually a sign
     that someone widened a scorer weight without adding a fixture,
     which is not comparable.

If you intentionally change scoring, add a new dated baseline under
`reports/` and update `BASELINE_PATH` — do not just relax the band.
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

BASELINE_PATH = Path(__file__).parent.parent / "reports" / "baseline-2026-06-20.json"
FIXTURES = Path(__file__).parent / "fixtures"

MAX_REGRESSION = 0.05
MAX_IMPROVEMENT = 0.30


def _fixture_records(query: SourceQuery):
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


def test_baseline_file_exists():
    assert BASELINE_PATH.exists(), (
        f"Missing baseline at {BASELINE_PATH}. "
        "Every PR that touches scoring must first update the baseline."
    )


def test_baseline_shape_is_stable():
    baseline = json.loads(BASELINE_PATH.read_text())
    assert set(baseline.keys()) >= {"query", "rows"}
    row_sources = {row["source"] for row in baseline["rows"]}
    assert row_sources == {
        "wikimedia",
        "archive_org",
        "peertube",
        "common_crawl",
        "__total__",
    }, (
        f"Baseline row set changed to {row_sources}. If a source was "
        "removed or renamed, freeze a new baseline instead of editing "
        "this test."
    )


def test_mean_quality_within_regression_band():
    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_terms = baseline["query"]["terms"]
    query = SourceQuery(
        terms=list(baseline_terms),
        max_results=int(baseline["query"]["max_results"]),
        language=baseline["query"].get("language"),
    )

    baseline_by_source = {row["source"]: row for row in baseline["rows"]}

    rerun = run_comparison(query, _fixture_records(query), notes="regression-check")

    failures: list[str] = []
    for row in rerun:
        if row.source not in baseline_by_source:
            continue
        base = baseline_by_source[row.source]["mean_quality"]
        drift = row.mean_quality - base
        if drift < -MAX_REGRESSION:
            failures.append(
                f"{row.source}: mean_quality regressed by {-drift:.4f} "
                f"(baseline={base:.4f}, current={row.mean_quality:.4f}, "
                f"max_regression={MAX_REGRESSION}). Adjust scorer or refresh baseline."
            )
        if drift > MAX_IMPROVEMENT:
            failures.append(
                f"{row.source}: mean_quality jumped by {drift:.4f} "
                f"(baseline={base:.4f}, current={row.mean_quality:.4f}, "
                f"max_improvement={MAX_IMPROVEMENT}). Freeze a new baseline "
                "so future PRs are compared against the new ceiling."
            )

    if failures:
        pytest.fail("\n".join(failures))


def test_license_clean_count_never_regresses():
    baseline = json.loads(BASELINE_PATH.read_text())
    query = SourceQuery(
        terms=list(baseline["query"]["terms"]),
        max_results=int(baseline["query"]["max_results"]),
        language=baseline["query"].get("language"),
    )
    baseline_by_source = {row["source"]: row for row in baseline["rows"]}
    rerun = run_comparison(query, _fixture_records(query), notes="regression-check")

    for row in rerun:
        base = baseline_by_source.get(row.source)
        if not base:
            continue
        assert row.n_license_clean >= base["n_license_clean"], (
            f"{row.source}: n_license_clean regressed from "
            f"{base['n_license_clean']} to {row.n_license_clean}. "
            "A license-classification change made us drop clean records."
        )
