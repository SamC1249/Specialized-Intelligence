"""Fixture-baseline regression lock — AGENTS.md rule #3.

Re-runs the comparison harness against the checked-in fixtures and
asserts every per-source aggregate matches the frozen baseline in
``reports/baseline-2026-06-20.json`` within a small tolerance. Any
future PR that "improves" the pipeline must either match the baseline
or explicitly re-baseline (with an entry in the daily plan explaining
why).

This closes weakness **W2** from ``docs/plan-2026-08-25.md``: nothing
in CI previously compared new runs against the frozen baseline, so a
subtle refactor of the quality scorer could silently regress
downstream corpus quality.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "reports" / "baseline-2026-06-20.json"
FIXTURES = Path(__file__).parent / "fixtures"

FLOAT_TOL = 1e-3


def _current_by_source(query: SourceQuery) -> dict:
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


def test_fixture_baseline_matches_committed_report():
    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_rows = {row["source"]: row for row in baseline["rows"]}
    query_terms = baseline["query"]["terms"]
    query = SourceQuery(
        terms=query_terms,
        max_results=baseline["query"]["max_results"],
        language=baseline["query"]["language"],
    )

    rows = run_comparison(query, _current_by_source(query), notes="fixture-baseline")
    current = {row.source: row for row in rows}

    assert set(current) == set(baseline_rows), (
        f"source set drift: current={sorted(current)} baseline={sorted(baseline_rows)}"
    )

    failures = []
    for source, row in current.items():
        base = baseline_rows[source]
        checks = {
            "n_records": row.n_records == base["n_records"],
            "n_license_clean": row.n_license_clean == base["n_license_clean"],
            "unique_authors": row.unique_authors == base["unique_authors"],
            "total_duration_s": abs(row.total_duration_s - base["total_duration_s"]) <= 1e-3,
            "mean_quality": abs(row.mean_quality - base["mean_quality"]) <= FLOAT_TOL,
            "p50_quality": abs(row.p50_quality - base["p50_quality"]) <= FLOAT_TOL,
            "p90_quality": abs(row.p90_quality - base["p90_quality"]) <= FLOAT_TOL,
        }
        for field, ok in checks.items():
            if not ok:
                failures.append(
                    f"{source}.{field}: current={getattr(row, field)!r} baseline={base[field]!r}"
                )

    if failures:
        pytest.fail(
            "Fixture-baseline regression (see AGENTS.md rule #3). "
            "Either fix the change or re-baseline explicitly:\n  " + "\n  ".join(failures)
        )
