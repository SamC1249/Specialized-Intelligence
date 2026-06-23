"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.audit import audit_records
from specint.compare import run_comparison
from specint.compare.strategies import compare_strategies, strategy_overlap_matrix
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


def _records_from_fixtures(only: set[str] | None = None) -> list:
    """Load every adapter's offline fixture and return the parsed records.

    This is the reproducible, no-network corpus that strategy comparison
    and audit run on inside CI.
    """
    from pathlib import Path

    from specint.records import SourceQuery

    fixtures_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
    query = SourceQuery(terms=DEFAULT_TERMS, max_results=50)
    all_records: list = []
    fixture_map = {
        "wikimedia": ("wikimedia/search_pasta.json", "json"),
        "archive_org": ("archive_org/search_cooking.json", "json"),
        "peertube": ("peertube/search_cooking.json", "json"),
        "common_crawl": ("common_crawl/recipe_page.html", "text"),
    }
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        rel, kind = fixture_map.get(slug, ("", ""))
        if not rel:
            continue
        path = fixtures_dir / rel
        if not path.exists():
            continue
        adapter = cls()
        raw = json.loads(path.read_text()) if kind == "json" else path.read_text()
        try:
            all_records.extend(adapter.parse(raw, query))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[warn] {slug} parse failed: {exc}", file=sys.stderr)
    return all_records


def _cmd_audit(args: argparse.Namespace) -> int:
    records = _records_from_fixtures()
    report = audit_records(records)
    payload = report.to_dict()
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"audit-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_strategies(args: argparse.Namespace) -> int:
    records = _records_from_fixtures()
    results = compare_strategies(records, k=args.top_k, seed=args.seed)
    matrix = strategy_overlap_matrix(results)
    payload = {
        "k": args.top_k,
        "seed": args.seed,
        "strategies": [r.to_dict() for r in results],
        "overlap_jaccard": matrix,
    }
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"strategies-{date.today().isoformat()}.json"
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
    p_cmp.set_defaults(func=_cmd_compare)

    p_audit = sub.add_parser("audit", help="cuisine/language/license bias audit (offline fixtures)")
    p_audit.add_argument("--output", help="output JSON path")
    p_audit.set_defaults(func=_cmd_audit)

    p_strat = sub.add_parser(
        "strategies",
        help="systematic comparison of selection strategies (quality, wm-utility, license-confidence, random)",
    )
    p_strat.add_argument("--top-k", type=int, default=10)
    p_strat.add_argument("--seed", type=int, default=1729)
    p_strat.add_argument("--output", help="output JSON path")
    p_strat.set_defaults(func=_cmd_strategies)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
