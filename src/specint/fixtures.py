"""Fixture-corpus loader shared by the CLI and the e2e test.

Fixtures live under `tests/fixtures/<source>/`. Each adapter's `parse`
contract is pure, so we can feed a checked-in blob through it offline
and treat the result as the canonical fixture corpus.

If a fixture directory is missing, the loader returns an empty list for
that source rather than raising — this keeps `python -m specint
compare --fixtures` usable in environments that only shipped a subset
of the fixtures.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"


def _load_json(rel: str) -> Any:
    path = FIXTURES_DIR / rel
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_text(rel: str) -> str | None:
    path = FIXTURES_DIR / rel
    if not path.exists():
        return None
    return path.read_text()


def _wikimedia(query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    source = WikimediaCommonsSource()
    for rel in ("wikimedia/search_pasta.json", "wikimedia/search_multilingual.json"):
        blob = _load_json(rel)
        if blob is not None:
            records.extend(source.parse(blob, query))
    return records


def _archive_org(query: SourceQuery) -> list[VideoRecord]:
    blob = _load_json("archive_org/search_cooking.json")
    if blob is None:
        return []
    return ArchiveOrgSource().parse(blob, query)


def _peertube(query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    source = PeerTubeSource()
    for rel in ("peertube/search_cooking.json", "peertube/search_french.json"):
        blob = _load_json(rel)
        if blob is not None:
            records.extend(source.parse(blob, query))
    return records


def _common_crawl(query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    source = CommonCrawlRecipeSource()
    for rel, page_url in (
        ("common_crawl/recipe_page.html", "https://example.test/recipes/garlic-butter-pasta"),
        (
            "common_crawl/recipe_page_youtube_embed.html",
            "https://example.test/recipes/broccoli-cheddar-soup",
        ),
    ):
        html = _load_text(rel)
        if html is None:
            continue
        records.extend(source.parse({"html": html, "url": page_url}, query))
    return records


_LOADERS: dict[str, Callable[[SourceQuery], list[VideoRecord]]] = {
    "wikimedia": _wikimedia,
    "archive_org": _archive_org,
    "peertube": _peertube,
    "common_crawl": _common_crawl,
}


def load_fixture_corpus(query: SourceQuery) -> dict[str, list[VideoRecord]]:
    """Return per-source records parsed from the checked-in fixtures."""
    return {slug: loader(query) for slug, loader in _LOADERS.items()}
