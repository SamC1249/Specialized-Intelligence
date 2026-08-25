"""Fixture-driven records used by the offline harness and CI.

`load_fixture_records` returns the same records as the e2e test — a
single source of truth so `python -m specint compare --fixtures` and
tests can never drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.peertube_federation import PeerTubeFederationSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCreativeCommonsSource

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _json(path: str):
    return json.loads((FIXTURES / path).read_text())


def _text(path: str) -> str:
    return (FIXTURES / path).read_text()


def load_fixture_records(query: SourceQuery | None = None) -> dict[str, list[VideoRecord]]:
    query = query or SourceQuery(terms=["cooking", "recipe"], max_results=25)
    return {
        "wikimedia": WikimediaCommonsSource().parse(_json("wikimedia/search_pasta.json"), query),
        "archive_org": ArchiveOrgSource().parse(_json("archive_org/search_cooking.json"), query),
        "peertube": PeerTubeSource().parse(_json("peertube/search_cooking.json"), query),
        "peertube_federation": PeerTubeFederationSource(instances=[]).parse(
            {
                "https://framatube.org": _json("peertube_federation/framatube_search.json"),
                "https://tilvids.com": _json("peertube_federation/tilvids_search.json"),
            },
            query,
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": _text("common_crawl/recipe_page.html"),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
        "youtube_cc": YouTubeCreativeCommonsSource().parse(
            _json("youtube_cc/search_cooking.json"), query
        ),
    }
