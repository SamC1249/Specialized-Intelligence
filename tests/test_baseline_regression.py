"""Baseline regression fence.

Reproduces the fixture-driven comparison against the checked-in
`reports/baseline-2026-06-20.json` and asserts new numbers do not
drift beyond a tight tolerance. If you *intend* to change the
baseline (e.g. you added a scoring component), re-run the harness,
overwrite the JSON, and land the diff explicitly — never
autoregenerate.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"
BASELINE = Path(__file__).parent.parent / "reports" / "baseline-2026-06-20.json"

REL_TOL = 1e-6
ABS_TOL = 1e-9


def _fresh_rows() -> list[dict]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = {
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
    rows = run_comparison(query, by_source, notes="fixture-baseline")
    return [r.model_dump(mode="json") for r in rows]


def _index(rows: list[dict]) -> dict[str, dict]:
    return {r["source"]: r for r in rows}


@pytest.fixture(scope="module")
def baseline() -> dict[str, dict]:
    payload = json.loads(BASELINE.read_text())
    return _index(payload["rows"])


@pytest.fixture(scope="module")
def current() -> dict[str, dict]:
    return _index(_fresh_rows())


def test_baseline_row_coverage(baseline: dict[str, dict], current: dict[str, dict]) -> None:
    assert set(current) == set(baseline), (
        f"row set drifted; missing={set(baseline) - set(current)}, "
        f"extra={set(current) - set(baseline)}"
    )


COUNTS = ("n_records", "n_license_clean", "unique_authors")
FLOATS = ("mean_quality", "p50_quality", "p90_quality", "total_duration_s")


@pytest.mark.parametrize("field", COUNTS)
def test_counts_exact_match(
    field: str, baseline: dict[str, dict], current: dict[str, dict]
) -> None:
    for src, row in baseline.items():
        assert current[src][field] == row[field], (
            f"{src}.{field} regressed: baseline={row[field]}, current={current[src][field]}"
        )


@pytest.mark.parametrize("field", FLOATS)
def test_floats_match_within_tolerance(
    field: str, baseline: dict[str, dict], current: dict[str, dict]
) -> None:
    for src, row in baseline.items():
        assert math.isclose(current[src][field], row[field], rel_tol=REL_TOL, abs_tol=ABS_TOL), (
            f"{src}.{field} drifted beyond tolerance: "
            f"baseline={row[field]}, current={current[src][field]}"
        )
