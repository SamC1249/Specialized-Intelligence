"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import (
    diff_reports,
    load_records_by_source,
    load_suite,
    run_comparison,
    run_matrix,
)
from specint.quality import available_scorers
from specint.records import SourceQuery, SourceQuerySuite
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _write_report(path: Path, payload: dict[str, Any], quiet: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(text)
    if not quiet:
        print(text)


def _cmd_compare(args: argparse.Namespace) -> int:
    if args.scorer not in available_scorers():
        print(
            f"unknown scorer {args.scorer!r}; available: {available_scorers()}",
            file=sys.stderr,
        )
        return 2

    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        by_source = dict(load_records_by_source(query, only=only))
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

    rows = run_comparison(query, by_source, notes=args.notes or "", scorer=args.scorer)
    payload = {
        "query": query.model_dump(mode="json"),
        "scorer": args.scorer,
        "rows": [r.model_dump(mode="json") for r in rows],
    }

    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"compare-{date.today().isoformat()}.json"
    )
    _write_report(out_path, payload, quiet=bool(args.quiet))
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    if args.scorer not in available_scorers():
        print(
            f"unknown scorer {args.scorer!r}; available: {available_scorers()}",
            file=sys.stderr,
        )
        return 2
    if not args.fixtures:
        print(
            "the matrix subcommand currently only supports --fixtures; live matrix runs are TBD.",
            file=sys.stderr,
        )
        return 2

    by_query_source = load_suite()
    queries = []
    for key in by_query_source:
        # key is `terms=a|b|c;max=25;lang=`
        terms_part = key.split(";", 1)[0]
        terms = [t for t in terms_part.removeprefix("terms=").split("|") if t]
        queries.append(SourceQuery(terms=terms, max_results=args.max_results))

    suite = SourceQuerySuite(name=args.name, queries=queries)
    rows = run_matrix(suite, by_query_source, notes=args.notes or "", scorer=args.scorer)

    payload = {
        "suite": suite.model_dump(mode="json"),
        "scorer": args.scorer,
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"matrix-{date.today().isoformat()}.json"
    )
    _write_report(out_path, payload, quiet=bool(args.quiet))
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    a = json.loads(Path(args.report_a).read_text())
    b = json.loads(Path(args.report_b).read_text())
    rows = diff_reports(a, b)
    payload = {
        "report_a": os.fspath(args.report_a),
        "report_b": os.fspath(args.report_b),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out_path = Path(args.output) if args.output else None
    if out_path:
        _write_report(out_path, payload, quiet=bool(args.quiet))
    else:
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
        "--scorer",
        default="v1",
        choices=available_scorers(),
        help="quality scorer name",
    )
    p_cmp.add_argument("--quiet", action="store_true", help="do not echo the report to stdout")
    p_cmp.set_defaults(func=_cmd_compare)

    p_matrix = sub.add_parser("matrix", help="multi-query benchmark matrix")
    p_matrix.add_argument("--fixtures", action="store_true")
    p_matrix.add_argument("--name", default="cooking-suite")
    p_matrix.add_argument("--max-results", type=int, default=25)
    p_matrix.add_argument("--output")
    p_matrix.add_argument("--notes")
    p_matrix.add_argument(
        "--scorer",
        default="v1",
        choices=available_scorers(),
    )
    p_matrix.add_argument("--quiet", action="store_true")
    p_matrix.set_defaults(func=_cmd_matrix)

    p_diff = sub.add_parser("diff", help="diff two comparison reports")
    p_diff.add_argument("report_a")
    p_diff.add_argument("report_b")
    p_diff.add_argument("--output")
    p_diff.add_argument("--quiet", action="store_true")
    p_diff.set_defaults(func=_cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
