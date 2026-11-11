"""Baseline regression: today's fixture harness output must stay within
tolerance of the newest committed `reports/baseline-*.json`.

Any intentional quality improvement updates the baseline in the same
PR; this test guarantees we **know** when a change moves a score.
Tolerance is deliberately small (±0.02 on `mean_quality`) because the
fixture corpus is tiny and deterministic.
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

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
TOLERANCE = 0.02


def _newest_baseline() -> Path | None:
    candidates = sorted(REPORTS_DIR.glob("baseline-*.json"))
    return candidates[-1] if candidates else None


def _run_fixture_harness(fixtures_dir: Path) -> list:
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
    return run_comparison(query, by_source, notes="fixture-baseline")


def test_mean_quality_within_tolerance_of_baseline(fixtures_dir: Path) -> None:
    baseline_path = _newest_baseline()
    if baseline_path is None:
        pytest.skip("no reports/baseline-*.json committed yet")

    baseline = json.loads(baseline_path.read_text())
    baseline_by_source = {row["source"]: row for row in baseline["rows"]}

    rows = _run_fixture_harness(fixtures_dir)

    for row in rows:
        src = row.source
        if src not in baseline_by_source:
            pytest.fail(
                f"source '{src}' appeared in harness output but is missing from "
                f"{baseline_path.name}; add it to the baseline in the same PR."
            )
        expected = baseline_by_source[src]["mean_quality"]
        actual = row.mean_quality
        drift = actual - expected
        assert abs(drift) <= TOLERANCE, (
            f"{src}: mean_quality drifted from baseline {expected:.4f} → {actual:.4f} "
            f"(Δ={drift:+.4f}; tolerance ±{TOLERANCE}). "
            f"If intentional, regenerate the baseline and commit it alongside this change."
        )


def test_record_counts_match_baseline_exactly(fixtures_dir: Path) -> None:
    baseline_path = _newest_baseline()
    if baseline_path is None:
        pytest.skip("no reports/baseline-*.json committed yet")

    baseline = json.loads(baseline_path.read_text())
    baseline_by_source = {row["source"]: row for row in baseline["rows"]}

    rows = _run_fixture_harness(fixtures_dir)
    for row in rows:
        expected = baseline_by_source.get(row.source)
        if expected is None:
            continue
        assert row.n_records == expected["n_records"], (
            f"{row.source}: n_records {row.n_records} != baseline {expected['n_records']}"
        )
        assert row.n_license_clean == expected["n_license_clean"], (
            f"{row.source}: n_license_clean {row.n_license_clean} != "
            f"baseline {expected['n_license_clean']}"
        )
