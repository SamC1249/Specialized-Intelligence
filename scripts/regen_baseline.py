"""Regenerate the offline benchmark report from checked-in fixtures.

Run:

    python scripts/regen_baseline.py

Emits `reports/baseline-YYYY-MM-DD.json`. Deterministic (no network,
no timestamps in the payload). Also used by
`tests/test_baseline_regression.py` to lock in "we shipped a real
number and didn't silently regress it".
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
REPORTS = Path(__file__).resolve().parents[1] / "reports"


def build_by_source(query: SourceQuery) -> dict[str, list]:
    wm = WikimediaCommonsSource().parse(
        json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
    )
    ao = ArchiveOrgSource().parse(
        json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), query
    )
    pt = PeerTubeSource().parse(
        json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), query
    )
    cc = CommonCrawlRecipeSource().parse(
        {
            "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        query,
    )
    return {"wikimedia": wm, "archive_org": ao, "peertube": pt, "common_crawl": cc}


def main() -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = build_by_source(query)
    rows = run_comparison(query, by_source, notes="fixture-baseline")
    payload = {
        "generated_at": datetime.now(UTC).date().isoformat(),
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"baseline-{date.today().isoformat()}.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
