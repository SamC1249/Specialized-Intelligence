"""`python -m specint` CLI.

Subcommands:
  * `sources`  — list registered source adapters.
  * `compare`  — run the quality-ranking harness; `--profile` selects
    a `QualityProfile` (use `--profile all` to emit every profile in
    one report, so baseline-vs-v2 diffs are trivial).
  * `dedupe`   — cross-source duplicate stats via `specint.dedupe`.
  * `yield`    — per-source yield estimate; see `specint.yield_estimator`.

All data-producing subcommands default to `--fixtures` (offline) when
`SPECINT_RUN_INTEGRATION` is not set to `1`, so CI never hits the
network.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint._fixtures import load_fixtures
from specint.compare import available_profiles, run_comparison
from specint.dedupe import dedupe_stats
from specint.records import SourceQuery
from specint.sources import REGISTRY
from specint.yield_estimator import estimate, to_rows

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _profiles_arg(value: str) -> list[str]:
    if value == "all":
        return available_profiles()
    if value not in available_profiles():
        raise argparse.ArgumentTypeError(
            f"unknown profile {value!r}; known: {available_profiles()}"
        )
    return [value]


def _collect_records(args: argparse.Namespace, query: SourceQuery):
    """Return `(by_source, exit_code)`. On refusal `by_source` is None."""
    only = set(args.only) if args.only else None
    if args.fixtures:
        return load_fixtures(query, only=only), 0
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return None, 2
    by_source: dict[str, list] = {}
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            by_source[slug] = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            by_source[slug] = []
    return by_source, 0


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source, rc = _collect_records(args, query)
    if by_source is None:
        return rc

    profiles = args.profile  # already normalized to list[str] by _profiles_arg
    rows_out = []
    for profile_name in profiles:
        rows = run_comparison(query, by_source, notes=args.notes or "", profile=profile_name)
        rows_out.extend(rows)

    payload = {
        "query": query.model_dump(mode="json"),
        "profiles": profiles,
        "rows": [r.model_dump(mode="json") for r in rows_out],
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


def _cmd_dedupe(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source, rc = _collect_records(args, query)
    if by_source is None:
        return rc

    flat = [r for records in by_source.values() for r in records]
    stats = dedupe_stats(flat, bucket_s=args.bucket_s)
    per_source = {
        slug: dedupe_stats(records, bucket_s=args.bucket_s)
        for slug, records in sorted(by_source.items())
    }
    payload = {
        "query": query.model_dump(mode="json"),
        "bucket_s": args.bucket_s,
        "per_source": per_source,
        "cross_source": stats,
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_yield(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source, rc = _collect_records(args, query)
    if by_source is None:
        return rc

    estimates = [
        estimate(
            source=slug,
            upstream_total_hits=len(records),
            records=records,
            batch_size=args.batch_size,
            notes=args.notes or "",
        )
        for slug, records in sorted(by_source.items())
    ]
    payload = {
        "query": query.model_dump(mode="json"),
        "batch_size": args.batch_size,
        "estimates": to_rows(estimates),
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True))
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
        "--profile",
        type=_profiles_arg,
        default=_profiles_arg("baseline"),
        help=f"quality profile; one of {available_profiles()} or 'all'",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_dedupe = sub.add_parser("dedupe", help="cross-source duplicate stats")
    p_dedupe.add_argument("--terms", nargs="*", help="search terms")
    p_dedupe.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_dedupe.add_argument("--max-results", type=int, default=25)
    p_dedupe.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_dedupe.add_argument("--output", help="output JSON path")
    p_dedupe.add_argument(
        "--bucket-s", type=float, default=30.0, help="duration bucket (seconds) for key hashing"
    )
    p_dedupe.set_defaults(func=_cmd_dedupe)

    p_yield = sub.add_parser("yield", help="per-source yield estimate")
    p_yield.add_argument("--terms", nargs="*", help="search terms")
    p_yield.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_yield.add_argument("--max-results", type=int, default=25)
    p_yield.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_yield.add_argument("--output", help="output JSON path")
    p_yield.add_argument("--notes", help="free-form note attached to every row")
    p_yield.add_argument(
        "--batch-size", type=int, default=50, help="hypothetical per-listing-call batch size"
    )
    p_yield.set_defaults(func=_cmd_yield)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
