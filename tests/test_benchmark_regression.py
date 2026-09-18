"""Benchmark regression guard.

Attack D1 from `docs/artifacts/2026-09-18-adversarial-findings.md`:
nothing in CI catches a scorer regression. This test re-runs the offline
harness across the current fixtures and asserts that per-source
``mean_quality`` has not dropped materially versus the committed
``reports/baseline-2026-06-20.json``.

If you *intend* to change scoring behaviour, regenerate the baseline
(document why in ``plan.md``) instead of loosening ``REGRESSION_EPSILON``.
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

REGRESSION_EPSILON = 0.02


def _load_fixture_records(fixtures_dir: Path, query: SourceQuery):
    return {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()),
            query,
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()),
            query,
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()),
            query,
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }


@pytest.fixture
def baseline_rows() -> dict[str, dict]:
    payload = json.loads(BASELINE_PATH.read_text())
    return {row["source"]: row for row in payload["rows"]}


def test_baseline_file_covers_every_registered_source(baseline_rows):
    from specint.sources import REGISTRY

    for slug in REGISTRY:
        assert slug in baseline_rows, (
            f"baseline missing source '{slug}'; regenerate "
            f"reports/baseline-2026-06-20.json after adding a source."
        )


def test_fixture_mean_quality_does_not_regress(fixtures_dir: Path, baseline_rows):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(
        query,
        _load_fixture_records(fixtures_dir, query),
        notes="regression-guard",
    )

    for row in rows:
        if row.source == "__total__":
            continue
        baseline = baseline_rows.get(row.source)
        assert baseline is not None, f"no baseline row for {row.source}"
        assert row.mean_quality + REGRESSION_EPSILON >= baseline["mean_quality"], (
            f"{row.source} mean_quality regressed: "
            f"{row.mean_quality:.4f} < {baseline['mean_quality']:.4f} - {REGRESSION_EPSILON}"
        )


def test_fixture_record_counts_do_not_shrink(fixtures_dir: Path, baseline_rows):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(
        query,
        _load_fixture_records(fixtures_dir, query),
        notes="regression-guard",
    )

    for row in rows:
        baseline = baseline_rows.get(row.source)
        if baseline is None:
            continue
        assert row.n_records >= baseline["n_records"], (
            f"{row.source} record count shrank: {row.n_records} < {baseline['n_records']}"
        )
