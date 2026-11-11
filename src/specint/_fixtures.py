"""Offline fixture loader shared by the CLI and tests.

Centralizes the path layout `tests/fixtures/<source>/<file>` so the
`compare --fixtures`, `dedupe --fixtures`, and `yield --fixtures` CLI
commands share a single source-of-truth for what the offline harness
runs over.
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
DEFAULT_FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _wikimedia(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    src = WikimediaCommonsSource()
    for name in sorted((fixtures_dir / "wikimedia").glob("*.json")):
        records.extend(src.parse(json.loads(name.read_text()), query))
    return records


def _archive(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    src = ArchiveOrgSource()
    for name in sorted((fixtures_dir / "archive_org").glob("*.json")):
        records.extend(src.parse(json.loads(name.read_text()), query))
    return records


def _peertube(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    src = PeerTubeSource()
    for name in sorted((fixtures_dir / "peertube").glob("*.json")):
        records.extend(src.parse(json.loads(name.read_text()), query))
    return records


def _common_crawl(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    src = CommonCrawlRecipeSource()
    for name in sorted((fixtures_dir / "common_crawl").glob("*.html")):
        payload = {"html": name.read_text(), "url": f"https://example.test/{name.stem}"}
        records.extend(src.parse(payload, query))
    return records


_LOADERS = {
    "wikimedia": _wikimedia,
    "archive_org": _archive,
    "peertube": _peertube,
    "common_crawl": _common_crawl,
}


def load_fixtures(
    query: SourceQuery,
    fixtures_dir: Path | None = None,
    only: set[str] | None = None,
) -> dict[str, list[VideoRecord]]:
    """Parse every checked-in fixture into records, keyed by source slug."""
    base = fixtures_dir or DEFAULT_FIXTURES
    out: dict[str, list[VideoRecord]] = {}
    for slug, loader in _LOADERS.items():
        if only and slug not in only:
            continue
        out[slug] = loader(base, query)
    return out


__all__ = ["DEFAULT_FIXTURES", "load_fixtures"]
