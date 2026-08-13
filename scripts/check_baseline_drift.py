"""Baseline-drift check.

Fails CI if the fixture-baseline source ordering by `mean_quality` diverges
from the most recent committed baseline in `reports/`. Human intent: any
adapter or scoring change that legitimately reshuffles the ranking must
commit an updated baseline in the same PR.

Invocation:  python scripts/check_baseline_drift.py
Exit codes:  0 = no drift; 1 = drift detected; 2 = internal error.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"

sys.path.insert(0, str(REPO_ROOT / "src"))

from specint.compare import run_comparison  # noqa: E402
from specint.records import SourceQuery  # noqa: E402
from specint.sources.archive_org import ArchiveOrgSource  # noqa: E402
from specint.sources.common_crawl import CommonCrawlRecipeSource  # noqa: E402
from specint.sources.peertube import PeerTubeSource  # noqa: E402
from specint.sources.wikimedia import WikimediaCommonsSource  # noqa: E402


def _latest_baseline() -> Path:
    candidates = sorted(REPORTS_DIR.glob("baseline-*.json"))
    if not candidates:
        print("No baseline-*.json found under reports/.", file=sys.stderr)
        sys.exit(2)
    return candidates[-1]


def _ordering(rows: list[dict]) -> list[str]:
    non_total = [r for r in rows if r["source"] != "__total__"]
    non_total.sort(key=lambda r: (-r["mean_quality"], r["source"]))
    return [r["source"] for r in non_total]


def main() -> int:
    fixtures = REPO_ROOT / "tests" / "fixtures"
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }

    rows = run_comparison(query, by_source, notes="drift-check")
    live_ordering = _ordering([r.model_dump(mode="json") for r in rows])

    baseline_path = _latest_baseline()
    baseline = json.loads(baseline_path.read_text())
    baseline_ordering = _ordering(baseline["rows"])

    if live_ordering != baseline_ordering:
        print(
            f"Source ordering drifted from {baseline_path.name}:\n"
            f"  baseline: {baseline_ordering}\n"
            f"  live:     {live_ordering}\n"
            "If this is intentional, commit an updated baseline under reports/ "
            "and note the reason in plan.md.",
            file=sys.stderr,
        )
        return 1

    print(f"Baseline ordering stable vs {baseline_path.name}: {live_ordering}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
