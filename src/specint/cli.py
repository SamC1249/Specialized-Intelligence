"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_ab_test, run_comparison
from specint.fixtures import load_fixture_records
from specint.quality import WEIGHTS, WEIGHTS_EXPERIMENTAL
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _write_and_echo(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug, records in load_fixture_records(query).items():
            if only and slug not in only:
                continue
            by_source[slug] = records
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
    _write_and_echo(payload, out_path)
    return 0


def _cmd_abtest(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    if not args.fixtures:
        print("abtest currently requires --fixtures", file=sys.stderr)
        return 2
    by_source = load_fixture_records(query)
    payload = run_ab_test(
        query=query,
        by_source=by_source,
        baseline_weights=WEIGHTS,
        experimental_weights=WEIGHTS_EXPERIMENTAL,
        notes=args.notes or "",
    )
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"procedural-abtest-{date.today().isoformat()}.json"
    )
    _write_and_echo(payload, out_path)
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
    p_cmp.set_defaults(func=_cmd_compare)

    p_ab = sub.add_parser("abtest", help="paired baseline-vs-experimental weight benchmark")
    p_ab.add_argument("--terms", nargs="*", help="search terms")
    p_ab.add_argument("--max-results", type=int, default=25)
    p_ab.add_argument("--fixtures", action="store_true", help="offline mode (required today)")
    p_ab.add_argument("--output", help="output JSON path")
    p_ab.add_argument("--notes", help="free-form note")
    p_ab.set_defaults(func=_cmd_abtest)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
