"""Load the checked-in test fixtures through the real adapters.

Kept out of `tests/` so the CLI (`python -m specint compare --fixtures`)
can consume the same code path without importing test-only helpers.

Every fixture path here is *canonical* — sources added to `REGISTRY`
must ship a matching fixture entry so the harness stays honest.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources import (
    ArchiveOrgSource,
    CommonCrawlRecipeSource,
    PeerTubeSource,
    WikimediaCommonsSource,
)

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text())


def _load_html(path: Path) -> str:
    return path.read_text()


def load_fixture_records(
    query: SourceQuery,
    fixtures_dir: Path | None = None,
    only: Iterable[str] | None = None,
) -> dict[str, list[VideoRecord]]:
    root = fixtures_dir or DEFAULT_FIXTURES_DIR
    wanted = set(only) if only else None
    out: dict[str, list[VideoRecord]] = {}

    if wanted is None or "wikimedia" in wanted:
        raw = _load_json(root / "wikimedia/search_pasta.json")
        out["wikimedia"] = WikimediaCommonsSource().parse(raw, query)

    if wanted is None or "archive_org" in wanted:
        raw = _load_json(root / "archive_org/search_cooking.json")
        out["archive_org"] = ArchiveOrgSource().parse(raw, query)

    if wanted is None or "peertube" in wanted:
        raw = _load_json(root / "peertube/search_cooking.json")
        out["peertube"] = PeerTubeSource().parse(raw, query)

    if wanted is None or "common_crawl" in wanted:
        html = _load_html(root / "common_crawl/recipe_page.html")
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {"html": html, "url": "https://example.test/recipes/garlic-butter-pasta"}, query
        )

    return out


__all__ = ["DEFAULT_FIXTURES_DIR", "load_fixture_records"]
