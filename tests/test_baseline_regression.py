"""Guard against silent drift in the comparison harness output.

Re-runs the harness against the checked-in fixtures and asserts that
the per-source `mean_quality`, `n_records`, and `n_license_clean` match
`reports/baseline-2026-06-20.json` within a small tolerance.

Any change to `quality/metrics.py`, `compare/harness.py`, or an adapter
parser that would move the numbers must ship a new baseline JSON *and*
a plan entry justifying the shift.
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

BASELINE = Path(__file__).parent.parent / "reports" / "baseline-2026-06-20.json"

TOL_QUALITY = 1e-6


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
    }


def test_fixture_baseline_is_stable(fixtures_dir: Path):
    baseline = json.loads(BASELINE.read_text())
    query = SourceQuery(**baseline["query"])
    rows = run_comparison(query, _build_by_source(fixtures_dir, query), notes="fixture-baseline")

    baseline_by_source = {r["source"]: r for r in baseline["rows"]}
    actual_by_source = {r.source: r for r in rows}

    assert set(actual_by_source) == set(baseline_by_source), (
        f"row set mismatch: actual={set(actual_by_source)} baseline={set(baseline_by_source)}"
    )

    for source, expected in baseline_by_source.items():
        actual = actual_by_source[source]
        assert actual.n_records == expected["n_records"], (
            f"{source}: n_records drift {actual.n_records} vs {expected['n_records']}"
        )
        assert actual.n_license_clean == expected["n_license_clean"], (
            f"{source}: n_license_clean drift "
            f"{actual.n_license_clean} vs {expected['n_license_clean']}"
        )
        assert actual.mean_quality == pytest.approx(expected["mean_quality"], abs=TOL_QUALITY), (
            f"{source}: mean_quality drift {actual.mean_quality} vs {expected['mean_quality']}"
        )
        assert actual.p50_quality == pytest.approx(expected["p50_quality"], abs=TOL_QUALITY)
        assert actual.p90_quality == pytest.approx(expected["p90_quality"], abs=TOL_QUALITY)


def test_baseline_report_is_well_formed():
    baseline = json.loads(BASELINE.read_text())
    assert "query" in baseline and "rows" in baseline
    assert baseline["query"]["terms"] == ["cooking", "recipe"]
    sources = {r["source"] for r in baseline["rows"]}
    assert "__total__" in sources
    total = next(r for r in baseline["rows"] if r["source"] == "__total__")
    per_source = sum(r["n_records"] for r in baseline["rows"] if r["source"] != "__total__")
    assert total["n_records"] == per_source
