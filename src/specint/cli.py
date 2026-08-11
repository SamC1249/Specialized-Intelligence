"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import (
    ablate,
    default_fixtures_dir,
    load_fixture_by_source,
    run_comparison,
    to_report,
)
from specint.quality import all_seed_terms
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _resolve_terms(args: argparse.Namespace) -> list[str]:
    if args.multilingual:
        langs = args.langs or None
        return all_seed_terms(langs)
    return args.terms or DEFAULT_TERMS


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else default_fixtures_dir()
        if fixtures_dir is not None:
            loaded = load_fixture_by_source(fixtures_dir, query)
            for slug, records in loaded.items():
                if only and slug not in only:
                    continue
                by_source[slug] = records
        else:
            for slug in REGISTRY:
                if only and slug not in only:
                    continue
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
    terms = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results)

    fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else default_fixtures_dir()
    if fixtures_dir is None:
        print(
            "no fixtures directory found; pass --fixtures-dir or set SPECINT_FIXTURES_DIR.",
            file=sys.stderr,
        )
        return 2
    by_source = load_fixture_by_source(fixtures_dir, query)
    rows = ablate(query, by_source)
    report = to_report(query, rows, notes=args.notes or "fixture-ablation")
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"ablate-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _add_query_args(p_cmp)
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument(
        "--fixtures-dir",
        help="path to the fixtures directory (default: $SPECINT_FIXTURES_DIR or ./tests/fixtures)",
    )
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_ab = sub.add_parser("ablate", help="weight-vector ablation on the fixture set (offline)")
    _add_query_args(p_ab)
    p_ab.add_argument(
        "--fixtures-dir",
        help="path to the fixtures directory (default: $SPECINT_FIXTURES_DIR or ./tests/fixtures)",
    )
    p_ab.add_argument("--output", help="output JSON path")
    p_ab.add_argument("--notes", help="notes attached to the ablation report")
    p_ab.set_defaults(func=_cmd_ablate)

    return p


def _add_query_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--terms", nargs="*", help="search terms")
    sp.add_argument("--max-results", type=int, default=25)
    sp.add_argument(
        "--multilingual",
        action="store_true",
        help="use curated per-language seed terms",
    )
    sp.add_argument(
        "--langs",
        nargs="*",
        help="restrict --multilingual to these ISO 639-1 codes",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
