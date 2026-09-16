"""Load bundled fixture payloads through each adapter's `parse` method.

Intent: give the CLI a real `--fixtures` mode (offline, no network) that
produces the *same* records the unit tests see, so `reports/ci-compare.json`
is a meaningful e2e artifact instead of a placebo of zeros.

Layout under a fixtures root (see `tests/fixtures/`):

  <root>/wikimedia/search_pasta.json
  <root>/archive_org/search_cooking.json
  <root>/peertube/search_cooking.json
  <root>/common_crawl/recipe_page.html

New adapters MUST register their fixture path in `FIXTURE_SPECS`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specint.records import SourceQuery, VideoRecord
from specint.sources import (
    ArchiveOrgSource,
    BaseSource,
    CommonCrawlRecipeSource,
    PeerTubeSource,
    WikimediaCommonsSource,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _load_common_crawl(path: Path) -> dict[str, str]:
    return {
        "html": path.read_text(),
        "url": "https://example.test/recipes/garlic-butter-pasta",
    }


@dataclass(frozen=True)
class FixtureSpec:
    slug: str
    source_cls: type[BaseSource]
    relpath: str
    loader: Callable[[Path], Any]


FIXTURE_SPECS: list[FixtureSpec] = [
    FixtureSpec("wikimedia", WikimediaCommonsSource, "wikimedia/search_pasta.json", _load_json),
    FixtureSpec("archive_org", ArchiveOrgSource, "archive_org/search_cooking.json", _load_json),
    FixtureSpec("peertube", PeerTubeSource, "peertube/search_cooking.json", _load_json),
    FixtureSpec(
        "common_crawl",
        CommonCrawlRecipeSource,
        "common_crawl/recipe_page.html",
        _load_common_crawl,
    ),
]


DEFAULT_FIXTURES_DIRS: tuple[str, ...] = (
    "tests/fixtures",
    "../tests/fixtures",
)


def resolve_fixtures_dir(explicit: str | Path | None = None) -> Path:
    """Locate the fixtures root.

    Priority: explicit arg → `SPECINT_FIXTURES_DIR` env → walk up from CWD
    looking for a `tests/fixtures` directory. Raises FileNotFoundError if
    none exists.
    """
    import os

    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("SPECINT_FIXTURES_DIR")
    if env:
        candidates.append(Path(env))
    cwd = Path.cwd()
    for base in (cwd, *cwd.parents):
        for rel in DEFAULT_FIXTURES_DIRS:
            candidates.append(base / rel)
    for c in candidates:
        if c.is_dir() and (c / "wikimedia").is_dir():
            return c.resolve()
    raise FileNotFoundError(
        "could not locate a tests/fixtures directory; set SPECINT_FIXTURES_DIR or pass --fixtures PATH"
    )


def load_by_source(
    query: SourceQuery, root: str | Path | None = None
) -> dict[str, list[VideoRecord]]:
    """Parse every registered fixture through its source's `parse`."""
    fixtures_root = resolve_fixtures_dir(root)
    out: dict[str, list[VideoRecord]] = {}
    for spec in FIXTURE_SPECS:
        raw = spec.loader(fixtures_root / spec.relpath)
        out[spec.slug] = list(spec.source_cls().parse(raw, query))
    return out
