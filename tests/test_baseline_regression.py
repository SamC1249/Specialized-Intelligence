"""Baseline-regression ratchet.

Rerun the fixture-driven comparison and assert per-source `mean_quality`
matches the checked-in baseline within a small tolerance. Prevents a
silent WEIGHTS or scorer edit from moving the baseline without the
maintainer *also* updating `reports/baseline-*.json` (and noting the
delta in `plan.md` / `docs/plan-*.md`).

If Coding-Agent legitimately improves the scorer:

    1. Regenerate `reports/baseline-YYYY-MM-DD.json` in the same PR.
    2. Update `BASELINE_PATH` below to point at the new file.
    3. Log the delta in `plan.md`.

Tolerance is intentionally tight; float noise is well under 1e-6 here
so anything above 5e-3 is a real semantic change.
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

REPO = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO / "reports" / "baseline-2026-06-20.json"
TOLERANCE_MEAN_QUALITY = 5e-3


def _load_baseline_by_source() -> dict[str, dict]:
    payload = json.loads(BASELINE_PATH.read_text())
    return {row["source"]: row for row in payload["rows"]}


def _regenerate_rows(fixtures_dir: Path):
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
    return query, run_comparison(query, by_source, notes="fixture-baseline")


@pytest.mark.skipif(not BASELINE_PATH.exists(), reason="no committed baseline yet")
def test_per_source_mean_quality_within_tolerance(fixtures_dir: Path) -> None:
    baseline = _load_baseline_by_source()
    _query, rows = _regenerate_rows(fixtures_dir)

    seen: list[str] = []
    for row in rows:
        seen.append(row.source)
        assert row.source in baseline, (
            f"source '{row.source}' not present in baseline; "
            f"if this is a new source, regenerate {BASELINE_PATH.name}"
        )
        expected = baseline[row.source]["mean_quality"]
        delta = abs(row.mean_quality - expected)
        assert delta <= TOLERANCE_MEAN_QUALITY, (
            f"mean_quality regression on {row.source}: "
            f"{row.mean_quality:.6f} vs baseline {expected:.6f} "
            f"(|delta|={delta:.6f} > {TOLERANCE_MEAN_QUALITY:.6f}). "
            f"If intentional, regenerate {BASELINE_PATH.name} in the same PR "
            f"and note the delta in plan.md."
        )

    baseline_sources = set(baseline.keys())
    assert set(seen) == baseline_sources, (
        f"source coverage drift: rerun produced {sorted(seen)} "
        f"but baseline covers {sorted(baseline_sources)}"
    )


@pytest.mark.skipif(not BASELINE_PATH.exists(), reason="no committed baseline yet")
def test_per_source_n_records_matches_baseline(fixtures_dir: Path) -> None:
    baseline = _load_baseline_by_source()
    _query, rows = _regenerate_rows(fixtures_dir)
    for row in rows:
        expected_n = baseline[row.source]["n_records"]
        assert row.n_records == expected_n, (
            f"n_records regression on {row.source}: "
            f"{row.n_records} vs baseline {expected_n}. "
            f"Fixtures likely changed; regenerate {BASELINE_PATH.name}."
        )
