"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_full_comparison
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCCSource

DEFAULT_TERMS = ["cooking", "recipe"]
_FIXTURES = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _load_fixtures(query: SourceQuery, only: set[str] | None) -> dict[str, list[VideoRecord]]:
    """Load offline fixtures for every registered source (or a subset)."""
    fx = _FIXTURES
    out: dict[str, list[VideoRecord]] = {}
    plans: list[tuple[str, callable[[], list[VideoRecord]]]] = [  # type: ignore[valid-type]
        (
            "wikimedia",
            lambda: WikimediaCommonsSource().parse(
                json.loads((fx / "wikimedia/search_pasta.json").read_text()), query
            ),
        ),
        (
            "archive_org",
            lambda: ArchiveOrgSource().parse(
                json.loads((fx / "archive_org/search_cooking.json").read_text()), query
            ),
        ),
        (
            "peertube",
            lambda: PeerTubeSource().parse(
                json.loads((fx / "peertube/search_cooking.json").read_text()), query
            ),
        ),
        (
            "common_crawl",
            lambda: CommonCrawlRecipeSource().parse(
                {
                    "html": (fx / "common_crawl/recipe_page.html").read_text(),
                    "url": "https://example.test/recipes/garlic-butter-pasta",
                },
                query,
            ),
        ),
        (
            "youtube_cc",
            lambda: YouTubeCCSource().parse(
                json.loads((fx / "youtube_cc/search_cooking.json").read_text()), query
            ),
        ),
    ]
    for slug, loader in plans:
        if only and slug not in only:
            continue
        try:
            out[slug] = loader()
        except FileNotFoundError:
            out[slug] = []
    return out


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if args.fixtures:
        by_source = _load_fixtures(query, only)
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        by_source = {}
        for slug, cls in REGISTRY.items():
            if only and slug not in only:
                continue
            try:
                by_source[slug] = list(cls().search(query))
            except Exception as exc:  # pragma: no cover - integration only
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                by_source[slug] = []

    result = run_full_comparison(
        query,
        by_source,
        notes=args.notes or "",
        detect_language=args.detect_language,
        apply_dedupe=args.dedupe,
    )
    payload = result.to_payload(query)

    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"compare-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument(
        "--dedupe",
        action="store_true",
        help="run cross-source dedupe and emit a __total_deduped__ row + dedupe report",
    )
    p_cmp.add_argument(
        "--detect-language",
        action="store_true",
        help="run offline heuristic language detector on records missing `language`",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
