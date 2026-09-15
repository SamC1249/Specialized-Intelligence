"""Emit ground-truth baseline reports from the checked-in test fixtures.

`python -m specint compare --fixtures` intentionally returns *empty*
by-source lists so it can be run in CI without any files present. When
we want a real, comparable report row (the kind PRs must beat) we load
the shipped `tests/fixtures/*` files instead. That is what this script
does. It writes:

  reports/compare-balanced-<date>.json
  reports/ablation-<date>.json
  reports/dedup-<date>.json

Run: `python scripts/emit_baseline_reports.py [--date YYYY-MM-DD]`.
"""

from __future__ import annotations

import argparse
import json
from datetime import date as date_cls
from pathlib import Path

from specint.compare import run_ablation, run_comparison
from specint.quality.dedup import deduplicate
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCCSource

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
REPORTS = REPO_ROOT / "reports"


def load_by_source(query: SourceQuery) -> dict[str, list]:
    return {
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
        "youtube_cc": YouTubeCCSource().parse(
            json.loads((FIXTURES / "youtube_cc/search_cooking.json").read_text()), query
        ),
    }


def _dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date_cls.today().isoformat())
    parser.add_argument("--notes", default="fixture-baseline")
    args = parser.parse_args()

    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_by_source(query)

    rows = run_comparison(query, by_source, notes=args.notes, profile="balanced")
    _dump(
        REPORTS / f"compare-balanced-{args.date}.json",
        {
            "query": query.model_dump(mode="json"),
            "profile": "balanced",
            "rows": [r.model_dump(mode="json") for r in rows],
        },
    )

    ablation = run_ablation(query, by_source, notes=args.notes)
    _dump(REPORTS / f"ablation-{args.date}.json", ablation)

    all_records = [r for slug in sorted(by_source) for r in by_source[slug]]
    _, dedup_report = deduplicate(all_records)
    _dump(
        REPORTS / f"dedup-{args.date}.json",
        {
            "query": query.model_dump(mode="json"),
            "notes": args.notes,
            **dedup_report.model_dump(mode="json"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
