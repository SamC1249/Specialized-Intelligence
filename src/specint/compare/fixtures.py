"""Helpers that drive the comparison harness against the committed fixture
bundle. Both the regression gate (`tests/test_benchmark_regression.py`)
and the baseline-generation script import this so the two can never
drift out of sync.

Only the *happy-path* fixtures are included so that adding adversarial
fixtures in future PRs does not silently shift the baseline numbers.
Adversarial payloads are exercised by `tests/test_sources_adversarial.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare.harness import run_comparison
from specint.records import BenchmarkResult, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"

HAPPY_PATH_FIXTURES: dict[str, str] = {
    "wikimedia": "wikimedia/search_pasta.json",
    "archive_org": "archive_org/search_cooking.json",
    "peertube": "peertube/search_cooking.json",
    "common_crawl": "common_crawl/recipe_page.html",
}

DEFAULT_TERMS = ["cooking", "recipe"]
DEFAULT_NOTES = "fixture-baseline"


def _parse_wikimedia(path: Path, query: SourceQuery):
    return WikimediaCommonsSource().parse(json.loads(path.read_text()), query)


def _parse_archive(path: Path, query: SourceQuery):
    return ArchiveOrgSource().parse(json.loads(path.read_text()), query)


def _parse_peertube(path: Path, query: SourceQuery):
    return PeerTubeSource().parse(json.loads(path.read_text()), query)


def _parse_common_crawl(path: Path, query: SourceQuery):
    return CommonCrawlRecipeSource().parse(
        {
            "html": path.read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        query,
    )


_PARSERS = {
    "wikimedia": _parse_wikimedia,
    "archive_org": _parse_archive,
    "peertube": _parse_peertube,
    "common_crawl": _parse_common_crawl,
}


def run_fixture_harness(
    terms: list[str] | None = None,
    notes: str = DEFAULT_NOTES,
) -> tuple[SourceQuery, list[BenchmarkResult]]:
    query = SourceQuery(terms=terms or DEFAULT_TERMS, max_results=25)
    by_source = {}
    for slug, rel in HAPPY_PATH_FIXTURES.items():
        path = FIXTURES_ROOT / rel
        if not path.exists():
            raise FileNotFoundError(f"missing fixture: {path}")
        by_source[slug] = _PARSERS[slug](path, query)
    rows = run_comparison(query, by_source, notes=notes)
    return query, rows


def serialise(query: SourceQuery, rows: list[BenchmarkResult]) -> dict:
    return {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
