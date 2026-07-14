"""Harness must be byte-deterministic for the same inputs.

Regression guard: if any adapter, scorer, or aggregation step becomes
non-deterministic (dict ordering leaks, timestamps folded into output,
random tie-breaking), this test catches it before a `reports/*.json`
comparison silently drifts.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _by_source() -> dict[str, list[VideoRecord]]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
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


def _serialise(rows) -> str:
    return json.dumps([r.model_dump(mode="json") for r in rows], sort_keys=True)


def test_run_comparison_is_deterministic() -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    a = run_comparison(query, _by_source(), notes="det")
    b = run_comparison(query, _by_source(), notes="det")
    assert _serialise(a) == _serialise(b), "run_comparison produced non-deterministic output"


def test_run_comparison_row_ordering_is_stable() -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, _by_source(), notes="det")
    sources_in_order = [r.source for r in rows]
    assert sources_in_order == [
        "archive_org",
        "common_crawl",
        "peertube",
        "wikimedia",
        "__total__",
    ], f"row ordering changed: {sources_in_order}"
