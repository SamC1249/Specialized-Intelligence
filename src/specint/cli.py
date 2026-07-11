"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import head_to_head, run_comparison
from specint.records import SourceQuery
from specint.sources import REGISTRY
from specint.sources.terms import known_languages
from specint.yield_estimator import estimate_yield, extract_listing_total

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_languages(_: argparse.Namespace) -> int:
    for lang in known_languages():
        print(lang)
    return 0


def _build_query(args: argparse.Namespace) -> SourceQuery:
    return SourceQuery(
        terms=args.terms or DEFAULT_TERMS,
        max_results=args.max_results,
        languages=list(args.languages or []),
    )


def _collect_by_source(args: argparse.Namespace, query: SourceQuery) -> dict[str, list]:
    only = set(args.only) if args.only else None
    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
        return by_source
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        raise SystemExit(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; pass --fixtures for an offline dry run."
        )
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            records = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            records = []
        by_source[slug] = records
    return by_source


def _cmd_compare(args: argparse.Namespace) -> int:
    query = _build_query(args)
    try:
        by_source = _collect_by_source(args, query)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload: dict[str, Any]
    if args.head_to_head:
        table = head_to_head(query, by_source, scorers=("v1", "v2"), notes=args.notes or "")
        payload = {
            "query": query.model_dump(mode="json"),
            "scorers": {
                name: [r.model_dump(mode="json") for r in rows] for name, rows in table.items()
            },
        }
    else:
        rows = run_comparison(
            query, by_source, notes=args.notes or "", scorer=args.scorer if args.scorer else None
        )
        payload = {
            "query": query.model_dump(mode="json"),
            "scorer": args.scorer or "v1",
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


def _cmd_yield(args: argparse.Namespace) -> int:
    fixtures_root = Path(args.fixtures_dir) if args.fixtures_dir else None
    if fixtures_root is None:
        print("--fixtures-dir is required (live yield estimation is future work)", file=sys.stderr)
        return 2

    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource
    from specint.sources.youtube import YouTubeCCSource

    query = SourceQuery(terms=args.terms or DEFAULT_TERMS, max_results=args.max_results)
    estimates: list[dict[str, Any]] = []

    def _load_json(rel: str) -> dict[str, Any]:
        return json.loads((fixtures_root / rel).read_text())

    sources_and_fixtures: list[tuple[str, Any, list]] = []
    try:
        wiki_raw = _load_json("wikimedia/search_pasta.json")
        sources_and_fixtures.append(
            ("wikimedia", wiki_raw, WikimediaCommonsSource().parse(wiki_raw, query))
        )
    except FileNotFoundError:
        pass
    try:
        ia_raw = _load_json("archive_org/search_cooking.json")
        sources_and_fixtures.append(
            ("archive_org", ia_raw, ArchiveOrgSource().parse(ia_raw, query))
        )
    except FileNotFoundError:
        pass
    try:
        pt_raw = _load_json("peertube/search_cooking.json")
        sources_and_fixtures.append(("peertube", pt_raw, PeerTubeSource().parse(pt_raw, query)))
    except FileNotFoundError:
        pass
    try:
        cc_html = (fixtures_root / "common_crawl/recipe_page.html").read_text()
        cc_records = CommonCrawlRecipeSource().parse(
            {"html": cc_html, "url": "https://example.test/r"}, query
        )
        sources_and_fixtures.append(("common_crawl", {"total": len(cc_records)}, cc_records))
    except FileNotFoundError:
        pass
    try:
        yt_raw = _load_json("youtube/videos_cooking.json")
        yt_total = {"pageInfo": {"totalResults": len(yt_raw.get("items", []))}}
        yt_records = YouTubeCCSource().parse(yt_raw, query)
        sources_and_fixtures.append(("youtube", yt_total, yt_records))
    except FileNotFoundError:
        pass

    for slug, raw, sample in sources_and_fixtures:
        total = extract_listing_total(slug, raw)
        est = estimate_yield(slug, sample, total)
        estimates.append(est.as_dict())

    payload = {
        "query": query.model_dump(mode="json"),
        "estimates": estimates,
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_langs = sub.add_parser("languages", help="list supported multilingual seed languages")
    p_langs.set_defaults(func=_cmd_languages)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms")
    p_cmp.add_argument("--languages", nargs="*", help="multilingual seed languages (BCP-47)")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument(
        "--scorer", choices=["v1", "v2"], default=None, help="quality scorer version"
    )
    p_cmp.add_argument(
        "--head-to-head",
        action="store_true",
        help="emit v1-and-v2 rows side by side in a single JSON",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_yield = sub.add_parser("yield", help="estimate license-clean yield per source")
    p_yield.add_argument("--terms", nargs="*", help="search terms")
    p_yield.add_argument("--max-results", type=int, default=25)
    p_yield.add_argument(
        "--fixtures-dir",
        help="path to a directory of source fixtures (currently the only supported mode)",
    )
    p_yield.add_argument("--output", help="output JSON path")
    p_yield.set_defaults(func=_cmd_yield)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
