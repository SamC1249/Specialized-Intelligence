"""Offline fixture loaders for the comparison harness.

These are committed sample payloads (not network-fetched) that let CI
produce a reproducible benchmark report without touching the network.
They are the same JSON/HTML shapes we unit-test the per-source parsers
against, duplicated under `sample_data/` so they ship inside the
installed package.

Each loader takes a `SourceQuery` and returns a list of `VideoRecord`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource, parse_recipe_html
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

SAMPLE_DIR = Path(__file__).parent / "sample_data"


def _load_json(name: str) -> dict:
    return json.loads((SAMPLE_DIR / name).read_text())


def _load_text(name: str) -> str:
    return (SAMPLE_DIR / name).read_text()


def _wikimedia(query: SourceQuery) -> list[VideoRecord]:
    return WikimediaCommonsSource().parse(_load_json("wikimedia_search_pasta.json"), query)


def _archive_org(query: SourceQuery) -> list[VideoRecord]:
    return ArchiveOrgSource().parse(_load_json("archive_org_search_cooking.json"), query)


def _peertube(query: SourceQuery) -> list[VideoRecord]:
    return PeerTubeSource().parse(_load_json("peertube_search_cooking.json"), query)


def _common_crawl(query: SourceQuery) -> list[VideoRecord]:
    src = CommonCrawlRecipeSource()
    records: list[VideoRecord] = []
    records.extend(
        src.parse(
            {
                "html": _load_text("common_crawl_recipe_page.html"),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        )
    )
    records.extend(
        parse_recipe_html(
            _load_text("common_crawl_recipe_page_cc_by.html"),
            "https://openrecipes.test/recipes/dal-tadka",
            query,
        )
    )
    return records


FIXTURE_LOADERS: dict[str, Callable[[SourceQuery], list[VideoRecord]]] = {
    "wikimedia": _wikimedia,
    "archive_org": _archive_org,
    "peertube": _peertube,
    "common_crawl": _common_crawl,
}
