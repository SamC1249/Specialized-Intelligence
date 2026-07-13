"""H3: monotonicity of `--dedupe` on the fixture-driven harness.

When we set `dedupe=True`, the total row's `n_records` must be
non-increasing versus the baseline. Per-source rows are unaffected.
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


def _build_by_source(fixtures_dir: Path, query: SourceQuery):
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


def test_dedupe_flag_is_monotonic_on_total(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _build_by_source(fixtures_dir, query)

    baseline_rows = run_comparison(query, by_source, notes="baseline")
    deduped_rows = run_comparison(query, by_source, notes="baseline", dedupe=True)

    baseline_total = next(r for r in baseline_rows if r.source == "__total__")
    deduped_total = next(r for r in deduped_rows if r.source == "__total__")

    assert deduped_total.n_records <= baseline_total.n_records
    per_source_baseline = {r.source: r for r in baseline_rows if r.source != "__total__"}
    per_source_deduped = {r.source: r for r in deduped_rows if r.source != "__total__"}
    assert per_source_baseline.keys() == per_source_deduped.keys()
    for slug, row in per_source_baseline.items():
        assert per_source_deduped[slug].n_records == row.n_records

    assert "dedupe=on" in deduped_total.notes
    assert "dedupe=on" not in baseline_total.notes
