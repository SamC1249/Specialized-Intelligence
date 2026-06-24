"""Source adapters. Each adapter subclasses `BaseSource`.

Adding a new source:
  1. Create a new module in this package.
  2. Implement `parse(raw)` (pure) and `search(query)` (may do I/O).
  3. Register it in `REGISTRY` below.
  4. Add a fixture under `tests/fixtures/<source>/` and a unit test.
  5. Make sure the comparison harness picks it up automatically via `REGISTRY`.
"""

from __future__ import annotations

from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.base import BaseSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REGISTRY: dict[str, type[BaseSource]] = {
    "wikimedia": WikimediaCommonsSource,
    "archive_org": ArchiveOrgSource,
    "peertube": PeerTubeSource,
    "common_crawl": CommonCrawlRecipeSource,
}

__all__ = [
    "REGISTRY",
    "ArchiveOrgSource",
    "BaseSource",
    "CommonCrawlRecipeSource",
    "PeerTubeSource",
    "WikimediaCommonsSource",
]
