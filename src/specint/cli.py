"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import dedup_report_payload, run_comparison, run_dedup
from specint.quality import check_records, summarize
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


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
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
        # No live calls in --fixtures mode; the harness reports zeros so CI is reproducible.
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

    rows = run_comparison(query, by_source, notes=args.notes or "")
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


def _load_fixture_records(only: set[str] | None) -> dict[str, list[VideoRecord]]:
    from pathlib import Path as _P

    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    fixtures = _P(__file__).parent.parent.parent / "tests" / "fixtures"
    query = SourceQuery(terms=DEFAULT_TERMS, max_results=25)

    def _keep(slug: str) -> bool:
        return only is None or slug in only

    out: dict[str, list[VideoRecord]] = {}
    if _keep("wikimedia"):
        out["wikimedia"] = WikimediaCommonsSource().parse(
            json.loads((fixtures / "wikimedia" / "search_pasta.json").read_text()), query
        )
    if _keep("archive_org"):
        out["archive_org"] = ArchiveOrgSource().parse(
            json.loads((fixtures / "archive_org" / "search_cooking.json").read_text()), query
        )
    if _keep("peertube"):
        out["peertube"] = PeerTubeSource().parse(
            json.loads((fixtures / "peertube" / "search_cooking.json").read_text()), query
        )
    if _keep("common_crawl"):
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures / "common_crawl" / "recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        )
    dup_dir = fixtures / "cross_source_dupes"
    if dup_dir.exists():
        if _keep("wikimedia"):
            wm_path = dup_dir / "wikimedia_search.json"
            if wm_path.exists():
                out.setdefault("wikimedia", []).extend(
                    WikimediaCommonsSource().parse(json.loads(wm_path.read_text()), query)
                )
        if _keep("archive_org"):
            ar_path = dup_dir / "archive_org_search.json"
            if ar_path.exists():
                out.setdefault("archive_org", []).extend(
                    ArchiveOrgSource().parse(json.loads(ar_path.read_text()), query)
                )
    return out


def _cmd_dedup(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    if not args.fixtures:
        print(
            "dedup currently supports --fixtures only; add --fixtures to run offline.",
            file=sys.stderr,
        )
        return 2
    by_source = _load_fixture_records(only)
    rows = run_dedup(query, by_source, notes=args.notes or "")
    payload = dedup_report_payload(query, rows, notes=args.notes or "")
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"dedup-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_check_invariants(args: argparse.Namespace) -> int:
    only = set(args.only) if args.only else None
    by_source = _load_fixture_records(only)
    all_violations = []
    for _source, records in by_source.items():
        all_violations.extend(check_records(records))
    payload = summarize(all_violations)
    payload["violations"] = [str(v) for v in all_violations]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not all_violations else 1


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
    p_cmp.set_defaults(func=_cmd_compare)

    p_dedup = sub.add_parser("dedup", help="run the near-duplicate comparison harness")
    p_dedup.add_argument("--terms", nargs="*", help="search terms")
    p_dedup.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_dedup.add_argument("--max-results", type=int, default=25)
    p_dedup.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_dedup.add_argument("--output", help="output JSON path")
    p_dedup.add_argument("--notes", help="free-form note attached to every row")
    p_dedup.set_defaults(func=_cmd_dedup)

    p_inv = sub.add_parser("check-invariants", help="check I1-I6 invariants on fixtures")
    p_inv.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_inv.set_defaults(func=_cmd_check_invariants)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
