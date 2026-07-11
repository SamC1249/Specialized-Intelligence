"""Regenerate the head-to-head scorer report and the yield report.

Runs offline against the checked-in fixtures. Produces:
  - reports/compare-scorers-YYYY-MM-DD.json  (v1 vs v2 side-by-side)
  - reports/yield-YYYY-MM-DD.json            (per-source yield estimate)

The intention is CI-friendly reproducibility: given the same fixtures
and code, this script must emit byte-identical JSON.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from specint.compare import head_to_head
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube import YouTubeCCSource
from specint.yield_estimator import estimate_yield, extract_listing_total

FIXTURES = Path("tests/fixtures")
REPORTS = Path("reports")
TODAY = date.today().isoformat()


def _load_json(rel: str):
    return json.loads((FIXTURES / rel).read_text())


def _by_source(query: SourceQuery):
    wiki_raw = _load_json("wikimedia/search_pasta.json")
    ia_raw = _load_json("archive_org/search_cooking.json")
    pt_raw = _load_json("peertube/search_cooking.json")
    yt_raw = _load_json("youtube/videos_cooking.json")
    cc_html = (FIXTURES / "common_crawl/recipe_page.html").read_text()

    return {
        "wikimedia": (wiki_raw, WikimediaCommonsSource().parse(wiki_raw, query)),
        "archive_org": (ia_raw, ArchiveOrgSource().parse(ia_raw, query)),
        "peertube": (pt_raw, PeerTubeSource().parse(pt_raw, query)),
        "common_crawl": (
            {"total": None},
            CommonCrawlRecipeSource().parse(
                {"html": cc_html, "url": "https://example.test/r"}, query
            ),
        ),
        "youtube": (yt_raw, YouTubeCCSource().parse(yt_raw, query)),
    }


def _write(name: str, payload: dict) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def main() -> int:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    data = _by_source(query)
    records_by_source = {slug: recs for slug, (_, recs) in data.items()}

    table = head_to_head(query, records_by_source, scorers=("v1", "v2"), notes="fixture-baseline")
    payload = {
        "query": query.model_dump(mode="json"),
        "scorers": {
            name: [r.model_dump(mode="json") for r in rows] for name, rows in table.items()
        },
    }
    scorers_path = _write(f"compare-scorers-{TODAY}.json", payload)

    estimates = []
    for slug, (raw, records) in data.items():
        total = extract_listing_total(slug, raw)
        estimates.append(estimate_yield(slug, records, total).as_dict())
    yield_payload = {
        "query": query.model_dump(mode="json"),
        "estimates": estimates,
    }
    yield_path = _write(f"yield-{TODAY}.json", yield_payload)

    print(f"wrote {scorers_path}")
    print(f"wrote {yield_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
