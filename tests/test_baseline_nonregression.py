"""Guardrail: fixture-driven `compare` results must not regress against
the committed baseline in `reports/baseline-2026-06-20.json`.

Rationale
---------
Nothing in CI today prevents a well-meaning refactor from silently
dropping `mean_quality` by 20% on a source. This test locks the
bootstrap baseline in place with a small tolerance envelope. When a
future PR *intentionally* improves the scorer, the same PR must
regenerate the baseline and justify the delta in `docs/plan-*.md`.

Contract
--------
For every source row in the baseline:
  * `n_records`       must be exactly equal (fixtures are frozen).
  * `n_license_clean` must be exactly equal (license logic is frozen).
  * `mean_quality`    must be within `TOL_MEAN` of baseline.
  * `p50_quality`     must be within `TOL_PCT`  of baseline.
  * `p90_quality`     must be within `TOL_PCT`  of baseline.

If you *intend* to change these numbers, regenerate the baseline via:

    python -m specint compare --fixtures --terms cooking recipe \\
        --output reports/baseline-YYYY-MM-DD.json

and update this test to point at the new file in the same commit.
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

BASELINE_PATH = Path(__file__).resolve().parent.parent / "reports" / "baseline-2026-06-20.json"

TOL_MEAN = 0.03
TOL_PCT = 0.05


def _load_baseline() -> dict[str, dict]:
    payload = json.loads(BASELINE_PATH.read_text())
    return {row["source"]: row for row in payload["rows"]}


def _run_fixture_compare(fixtures_dir: Path) -> dict[str, dict]:
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
    rows = run_comparison(query, by_source, notes="fixture-baseline")
    return {r.source: r.model_dump(mode="json") for r in rows}


@pytest.mark.parametrize(
    "source",
    ["wikimedia", "archive_org", "peertube", "common_crawl", "__total__"],
)
def test_baseline_nonregression_per_source(fixtures_dir: Path, source: str) -> None:
    baseline = _load_baseline()
    current = _run_fixture_compare(fixtures_dir)

    assert source in baseline, f"baseline missing source {source!r}"
    assert source in current, f"current run missing source {source!r}"

    b = baseline[source]
    c = current[source]

    assert c["n_records"] == b["n_records"], (
        f"{source}: n_records regressed {b['n_records']} -> {c['n_records']} "
        "(fixtures are supposed to be frozen)"
    )
    assert c["n_license_clean"] == b["n_license_clean"], (
        f"{source}: n_license_clean regressed {b['n_license_clean']} -> {c['n_license_clean']}"
    )
    assert abs(c["mean_quality"] - b["mean_quality"]) <= TOL_MEAN, (
        f"{source}: mean_quality drifted by more than {TOL_MEAN} "
        f"(baseline={b['mean_quality']:.4f} current={c['mean_quality']:.4f})"
    )
    assert abs(c["p50_quality"] - b["p50_quality"]) <= TOL_PCT, (
        f"{source}: p50_quality drifted by more than {TOL_PCT}"
    )
    assert abs(c["p90_quality"] - b["p90_quality"]) <= TOL_PCT, (
        f"{source}: p90_quality drifted by more than {TOL_PCT}"
    )
