"""Fixture loader shared by the CLI and ``scripts/pipeline_dry_run.py``.

This is the single canonical mapping from each registered source to its
checked-in fixture under ``tests/fixtures/``. Keeping the mapping in
one place means CI's ``--fixtures`` smoke test and the e2e pipeline
dry-run exercise the same parser paths against the same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def parse_fixtures(
    query: SourceQuery,
    fixtures_dir: Path | None = None,
) -> dict[str, list[VideoRecord]]:
    fdir = fixtures_dir or DEFAULT_FIXTURES_DIR

    def _load(rel: str) -> dict:
        return json.loads((fdir / rel).read_text())

    return {
        "wikimedia": WikimediaCommonsSource().parse(_load("wikimedia/search_pasta.json"), query),
        "archive_org": ArchiveOrgSource().parse(_load("archive_org/search_cooking.json"), query),
        "peertube": PeerTubeSource().parse(_load("peertube/search_cooking.json"), query),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fdir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }
