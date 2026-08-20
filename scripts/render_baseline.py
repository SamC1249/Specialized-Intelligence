"""Render `reports/compare-2026-08-20.json` from fixtures.

Deterministic, offline, no network. Committed so we always have a
canonical baseline artifact for the day.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.europeana import EuropeanaSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures"


def main() -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
        "europeana": EuropeanaSource().parse(
            json.loads((FIXTURES / "europeana/search_cooking.json").read_text()), query
        ),
    }

    rows = run_comparison(query, by_source, notes="fixture-baseline")
    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = REPO / "reports" / "compare-2026-08-20.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
