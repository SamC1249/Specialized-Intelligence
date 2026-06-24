"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_ablation, run_comparison
from specint.contamination import Blocklist, filter_contaminated
from specint.records import SourceQuery
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

    if args.blocklist:
        bl = Blocklist.load(args.blocklist)
        for slug, records in list(by_source.items()):
            kept, _dropped = filter_contaminated(records, bl)
            by_source[slug] = kept

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


def _cmd_ablate(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if not args.fixtures and os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; pass --fixtures.",
            file=sys.stderr,
        )
        return 2

    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
    else:
        for slug, cls in REGISTRY.items():
            if only and slug not in only:
                continue
            try:
                by_source[slug] = list(cls().search(query))
            except Exception as exc:  # pragma: no cover - integration only
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                by_source[slug] = []

    payload = run_ablation(query, by_source, notes=args.notes or "")
    payload["query"] = query.model_dump(mode="json")
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"ablation-{date.today().isoformat()}.json"
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
    p_cmp.add_argument("--blocklist", help="path to a contamination blocklist JSONL")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="quality-component ablation harness")
    p_abl.add_argument("--terms", nargs="*", help="search terms")
    p_abl.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_abl.add_argument("--max-results", type=int, default=25)
    p_abl.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_abl.add_argument("--output", help="output JSON path")
    p_abl.add_argument("--notes", help="free-form note attached to every row")
    p_abl.set_defaults(func=_cmd_ablate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
