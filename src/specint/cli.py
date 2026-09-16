"""`python -m specint` CLI.

Subcommands:
  * `sources`             — list registered adapters.
  * `compare`             — run the comparison harness (fixtures or live).
  * `compare-to-baseline` — re-run the fixture harness and diff against
                            a saved baseline JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import compare_against_baseline, run_comparison
from specint.fixtures import load_all_fixtures
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _collect_by_source(
    query: SourceQuery,
    *,
    fixtures: bool,
    only: set[str] | None,
) -> dict[str, list] | None:
    if fixtures:
        loaded = load_all_fixtures(query)
        return {slug: records for slug, records in loaded.items() if not only or slug in only}
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1;"
            " pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return None
    by_source: dict[str, list] = {}
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            by_source[slug] = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            by_source[slug] = []
    return by_source


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source = _collect_by_source(query, fixtures=args.fixtures, only=only)
    if by_source is None:
        return 2

    rows = run_comparison(
        query,
        by_source,
        notes=args.notes or "",
        profile=args.profile,
        deduplicate_across_sources=args.deduplicate,
    )
    payload = {
        "query": query.model_dump(mode="json"),
        "profile": args.profile,
        "deduplicate": args.deduplicate,
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


def _cmd_compare_to_baseline(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"baseline not found: {baseline_path}", file=sys.stderr)
        return 2

    baseline_payload = json.loads(baseline_path.read_text())
    baseline_query = baseline_payload.get("query", {})
    terms = args.terms or baseline_query.get("terms") or DEFAULT_TERMS
    max_results = args.max_results or baseline_query.get("max_results") or 25
    profile = args.profile or baseline_payload.get("profile") or "baseline"
    deduplicate = args.deduplicate
    if deduplicate is None:
        deduplicate = bool(baseline_payload.get("deduplicate", False))

    query = SourceQuery(terms=list(terms), max_results=max_results)
    by_source = _collect_by_source(query, fixtures=True, only=None)
    assert by_source is not None
    current_rows = run_comparison(
        query,
        by_source,
        notes="compare-to-baseline",
        profile=profile,
        deduplicate_across_sources=deduplicate,
    )

    report = compare_against_baseline(
        baseline_path,
        current_rows,
        tolerance_abs=args.tolerance,
    )
    payload: dict[str, Any] = report.to_dict()
    payload["query"] = query.model_dump(mode="json")
    payload["profile"] = profile
    payload["deduplicate"] = deduplicate

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))

    if not report.ok:
        print(
            f"regression: {len(report.regressions)} metric(s) fell below tolerance"
            f" ({args.tolerance})",
            file=sys.stderr,
        )
        return 1
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
        "--profile",
        default="baseline",
        help="scoring profile name (see specint.quality.profiles.PROFILES)",
    )
    p_cmp.add_argument(
        "--deduplicate",
        action="store_true",
        help="collapse cross-source duplicates in the __total__ row",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_reg = sub.add_parser(
        "compare-to-baseline",
        help="rerun the fixture harness and diff against a saved baseline JSON",
    )
    p_reg.add_argument("--baseline", required=True, help="path to a saved compare JSON")
    p_reg.add_argument("--terms", nargs="*", help="override baseline terms")
    p_reg.add_argument("--max-results", type=int, default=0)
    p_reg.add_argument("--profile", help="override baseline scoring profile")
    p_reg.add_argument(
        "--deduplicate",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="override baseline dedup setting",
    )
    p_reg.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="absolute tolerance below which a metric drop is a regression",
    )
    p_reg.add_argument("--output", help="optional JSON output for the diff")
    p_reg.set_defaults(func=_cmd_compare_to_baseline)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
