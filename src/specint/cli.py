"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]

FIXTURE_PATHS: dict[str, tuple[str, ...]] = {
    "wikimedia": ("wikimedia/search_pasta.json",),
    "archive_org": ("archive_org/search_cooking.json",),
    "peertube": ("peertube/search_cooking.json",),
    "common_crawl": ("common_crawl/recipe_page.html",),
    "youtube_cc": ("youtube_cc/search_cc_recipe.json",),
}


def _load_fixture_records(slug: str, fixtures_dir: Path, query: SourceQuery) -> list:
    cls = REGISTRY[slug]
    src = cls()
    records: list = []
    for rel in FIXTURE_PATHS.get(slug, ()):
        path = fixtures_dir / rel
        if not path.exists():
            continue
        if slug == "common_crawl":
            records.extend(
                src.parse(
                    {"html": path.read_text(), "url": f"https://example.test/{path.name}"}, query
                )
            )
        else:
            records.extend(src.parse(json.loads(path.read_text()), query))
    return records


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else None
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            if fixtures_dir is not None:
                by_source[slug] = _load_fixture_records(slug, fixtures_dir, query)
            else:
                by_source[slug] = []
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        for slug, cls in REGISTRY.items():
            if only and slug not in only:
                continue
            try:
                records = list(cls().search(query))
            except Exception as exc:  # pragma: no cover - integration only
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                records = []
            by_source[slug] = records

    rows = run_comparison(query, by_source, notes=args.notes or "", dedup=not args.no_dedup)
    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }

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
    p_cmp.add_argument(
        "--fixtures-dir",
        help="directory of fixture files to parse in offline mode (default: empty rows)",
    )
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument(
        "--no-dedup",
        action="store_true",
        help="disable cross-source deduplication when computing the __total__ row",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
