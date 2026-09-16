"""Load canonical offline fixtures shared by the CLI and tests.

The seed CLI used to hardcode empty lists in `--fixtures` mode. That
made the offline harness a no-op that could not detect regressions. We
now ship a canonical fixture manifest here so `compare --fixtures` and
`compare-to-baseline` produce a real, deterministic set of records.

If new fixtures are added under `tests/fixtures/`, register them in
`FIXTURE_MANIFEST` below and add a unit test that loads them.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"


FIXTURE_MANIFEST: dict[str, list[dict[str, str]]] = {
    "wikimedia": [
        {"kind": "json", "path": "wikimedia/search_pasta.json"},
        {"kind": "json", "path": "wikimedia/search_paella.json"},
    ],
    "archive_org": [
        {"kind": "json", "path": "archive_org/search_cooking.json"},
    ],
    "peertube": [
        {"kind": "json", "path": "peertube/search_cooking.json"},
        {"kind": "json", "path": "peertube/search_ramen.json"},
    ],
    "common_crawl": [
        {
            "kind": "html",
            "path": "common_crawl/recipe_page.html",
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        {
            "kind": "html",
            "path": "common_crawl/wikimedia_embed_page.html",
            "url": "https://example.test/recipes/commons-embed",
        },
    ],
}


def _load_wikimedia(entry: dict[str, str], query: SourceQuery) -> list[VideoRecord]:
    payload = json.loads((FIXTURES_ROOT / entry["path"]).read_text())
    return WikimediaCommonsSource().parse(payload, query)


def _load_archive(entry: dict[str, str], query: SourceQuery) -> list[VideoRecord]:
    payload = json.loads((FIXTURES_ROOT / entry["path"]).read_text())
    return ArchiveOrgSource().parse(payload, query)


def _load_peertube(entry: dict[str, str], query: SourceQuery) -> list[VideoRecord]:
    payload = json.loads((FIXTURES_ROOT / entry["path"]).read_text())
    return PeerTubeSource().parse(payload, query)


def _load_common_crawl(entry: dict[str, str], query: SourceQuery) -> list[VideoRecord]:
    html = (FIXTURES_ROOT / entry["path"]).read_text()
    return CommonCrawlRecipeSource().parse(
        {"html": html, "url": entry.get("url", "https://example.test/")},
        query,
    )


_LOADERS = {
    "wikimedia": _load_wikimedia,
    "archive_org": _load_archive,
    "peertube": _load_peertube,
    "common_crawl": _load_common_crawl,
}


def load_all_fixtures(query: SourceQuery) -> dict[str, list[VideoRecord]]:
    """Return a `{source_slug: [VideoRecord, ...]}` dict from disk fixtures.

    Missing fixture files are treated as empty; this keeps the CLI
    usable in shallow checkouts (e.g. sdist without tests/).
    """
    out: dict[str, list[VideoRecord]] = {}
    for slug, entries in FIXTURE_MANIFEST.items():
        loader = _LOADERS[slug]
        records: list[VideoRecord] = []
        for entry in entries:
            path = FIXTURES_ROOT / entry["path"]
            if not path.exists():
                continue
            records.extend(loader(entry, query))
        out[slug] = records
    return out
