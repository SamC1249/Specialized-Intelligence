"""Run the comparison harness deterministically against checked-in fixtures.

Why this exists:
    `python -m specint compare --fixtures` initialises every source's
    record list to `[]` and runs the harness over empty data — fine as a
    schema smoke-test, useless as a regression gate.

    This script instead loads each adapter's canonical fixture (the same
    ones `tests/test_e2e_compare.py` uses), feeds them through the
    adapter's pure `parse()`, scores them, and emits a deterministic
    `BenchmarkResult` list to a JSON file. CI compares the JSON against
    `reports/baseline-2026-06-20.json` with
    `scripts/check_benchmark_regression.py`.

Output JSON is structurally identical to what the CLI emits so existing
tooling continues to work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from specint.compare import run_comparison  # noqa: E402
from specint.records import SourceQuery  # noqa: E402
from specint.sources.archive_org import ArchiveOrgSource  # noqa: E402
from specint.sources.common_crawl import CommonCrawlRecipeSource  # noqa: E402
from specint.sources.peertube import PeerTubeSource  # noqa: E402
from specint.sources.wikimedia import WikimediaCommonsSource  # noqa: E402

DEFAULT_TERMS = ["cooking", "recipe"]
DEFAULT_NOTES = "fixture-baseline"

FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"


def _load_wikimedia(query: SourceQuery) -> list:
    payload = json.loads((FIXTURE_ROOT / "wikimedia" / "search_pasta.json").read_text())
    return WikimediaCommonsSource().parse(payload, query)


def _load_archive_org(query: SourceQuery) -> list:
    payload = json.loads((FIXTURE_ROOT / "archive_org" / "search_cooking.json").read_text())
    return ArchiveOrgSource().parse(payload, query)


def _load_peertube(query: SourceQuery) -> list:
    payload = json.loads((FIXTURE_ROOT / "peertube" / "search_cooking.json").read_text())
    return PeerTubeSource().parse(payload, query)


def _load_common_crawl(query: SourceQuery) -> list:
    html = (FIXTURE_ROOT / "common_crawl" / "recipe_page.html").read_text()
    payload = {
        "html": html,
        "url": "https://example.test/recipes/garlic-butter-pasta",
    }
    return CommonCrawlRecipeSource().parse(payload, query)


LOADERS = {
    "wikimedia": _load_wikimedia,
    "archive_org": _load_archive_org,
    "peertube": _load_peertube,
    "common_crawl": _load_common_crawl,
}


def build_benchmark(
    terms: list[str] | None = None,
    notes: str = DEFAULT_NOTES,
    only: list[str] | None = None,
) -> dict[str, Any]:
    query = SourceQuery(terms=terms or DEFAULT_TERMS, max_results=25)
    by_source: dict[str, list] = {}
    for slug, loader in LOADERS.items():
        if only and slug not in only:
            continue
        by_source[slug] = loader(query)
    rows = run_comparison(query, by_source, notes=notes)
    return {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--output",
        default=str(REPO_ROOT / "reports" / "compare-fixture.json"),
        help="where to write the deterministic benchmark JSON",
    )
    p.add_argument("--terms", nargs="*", help="override search terms")
    p.add_argument("--notes", default=DEFAULT_NOTES, help="note attached to every row")
    p.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p.add_argument(
        "--stdout",
        action="store_true",
        help="also pretty-print the resulting JSON to stdout",
    )
    args = p.parse_args(argv)

    payload = build_benchmark(terms=args.terms, notes=args.notes, only=args.only)
    rendered = json.dumps(payload, indent=2, sort_keys=True)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered + "\n")

    if args.stdout:
        print(rendered)
    print(f"wrote {out_path} ({len(payload['rows'])} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
