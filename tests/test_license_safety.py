"""License-safety invariants over every shipped fixture.

Hard-rule under `AGENTS.md`: a `media_url` (direct bytes we'd point a
training job at) must only be populated when the record's `License` is
redistributable. This test enforces that invariant by running every
adapter's `parse()` against every fixture we ship, and asserting the
invariant on each resulting record.

It also enforces that the `License.UNKNOWN` default never leaks a
`media_url`; a record whose license we could not classify is never
training-safe.

The test discovers fixtures dynamically so it keeps covering new
adapters as they land.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from specint.records import License, SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.flickr import FlickrCCSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.vimeo import VimeoCCSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"
QUERY = SourceQuery(terms=["cooking"], max_results=50)


def _common_crawl_load(path: Path) -> dict[str, Any]:
    return {"html": path.read_text(), "url": "https://example.test/recipes/fixture"}


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text())


_LOADERS: dict[str, tuple[Any, Callable[[Path], Any], str]] = {
    "wikimedia": (WikimediaCommonsSource(), _json_load, "*.json"),
    "archive_org": (ArchiveOrgSource(), _json_load, "*.json"),
    "peertube": (PeerTubeSource(), _json_load, "*.json"),
    "common_crawl": (CommonCrawlRecipeSource(), _common_crawl_load, "*.html"),
    "vimeo": (VimeoCCSource(), _json_load, "*.json"),
    "flickr": (FlickrCCSource(), _json_load, "*.json"),
}


def _discover() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for slug in REGISTRY:
        if slug not in _LOADERS:
            continue
        _, _, pattern = _LOADERS[slug]
        for fixture in sorted((FIXTURES / slug).glob(pattern)):
            out.append((slug, fixture))
    return out


DISCOVERED = _discover()


def test_discovery_sees_every_registered_source():
    """If a new source lands without a fixture we want this test to fail loudly."""
    seen = {slug for slug, _ in DISCOVERED}
    missing = set(REGISTRY) - seen - {"common_crawl"}  # common_crawl always has an .html fixture
    assert not missing, f"source(s) in REGISTRY without fixtures: {sorted(missing)}"


@pytest.mark.parametrize("slug,fixture", DISCOVERED, ids=[f"{s}:{p.name}" for s, p in DISCOVERED])
def test_media_url_only_when_license_is_redistributable(slug: str, fixture: Path):
    adapter, loader, _ = _LOADERS[slug]
    records: list[VideoRecord] = adapter.parse(loader(fixture), QUERY)
    for record in records:
        if record.media_url is not None:
            assert record.license.is_redistributable, (
                f"{slug}:{fixture.name} record {record.id} emits media_url under "
                f"non-redistributable license {record.license}"
            )
        if record.license is License.UNKNOWN:
            assert (
                record.media_url is None
            ), f"{slug}:{fixture.name} record {record.id} has UNKNOWN license but a media_url"
