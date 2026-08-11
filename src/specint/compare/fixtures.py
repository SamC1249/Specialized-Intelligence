"""Load the checked-in fixtures into `by_source` maps.

Fixtures live under `tests/fixtures/<source>/…`. The comparison harness
uses these as the offline ground truth for CI. Any new source adapter
must ship at least one fixture that this loader can pick up.

Callers pass an explicit `fixtures_dir` (typically resolved from
`--fixtures-dir` on the CLI or from `SPECINT_FIXTURES_DIR`). We keep the
loader inside `specint` (not in `tests/`) so users of the installed
package can point it at a fixtures folder shipped alongside their own
data.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def load_fixture_by_source(fixtures_dir: Path, query: SourceQuery) -> dict[str, list[VideoRecord]]:
    out: dict[str, list[VideoRecord]] = {slug: [] for slug in REGISTRY}
    wm = fixtures_dir / "wikimedia" / "search_pasta.json"
    if wm.exists():
        out["wikimedia"] = WikimediaCommonsSource().parse(json.loads(wm.read_text()), query)
    ao = fixtures_dir / "archive_org" / "search_cooking.json"
    if ao.exists():
        out["archive_org"] = ArchiveOrgSource().parse(json.loads(ao.read_text()), query)
    pt = fixtures_dir / "peertube" / "search_cooking.json"
    if pt.exists():
        out["peertube"] = PeerTubeSource().parse(json.loads(pt.read_text()), query)
    cc = fixtures_dir / "common_crawl" / "recipe_page.html"
    if cc.exists():
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {"html": cc.read_text(), "url": "https://example.test/recipes/garlic-butter-pasta"},
            query,
        )
    return out


def default_fixtures_dir() -> Path | None:
    """Best-effort locator for the repo fixtures folder.

    Search order:
      1. `$SPECINT_FIXTURES_DIR`.
      2. `<cwd>/tests/fixtures` (default when running from repo root).
    Returns `None` if nothing is found so callers can fail fast.
    """
    import os

    env = os.environ.get("SPECINT_FIXTURES_DIR")
    if env:
        p = Path(env)
        if p.exists():
            return p
    cand = Path.cwd() / "tests" / "fixtures"
    return cand if cand.exists() else None
