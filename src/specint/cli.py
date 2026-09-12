"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_comparison
from specint.quality import BATCH_SCORERS
from specint.queries import PRESETS, resolve_preset
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_scorers(_: argparse.Namespace) -> int:
    for name in sorted(BATCH_SCORERS):
        print(name)
    return 0


def _cmd_presets(_: argparse.Namespace) -> int:
    for name, terms in sorted(PRESETS.items()):
        print(f"{name}\t{','.join(terms)}")
    return 0


def _resolve_terms(args: argparse.Namespace) -> list[str]:
    if args.preset:
        try:
            return resolve_preset(args.preset)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
    return args.terms or DEFAULT_TERMS


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
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

    rows = run_comparison(
        query,
        by_source,
        notes=args.notes or "",
        scorer=args.scorer,
        dedup=args.dedup,
    )
    payload = {
        "query": query.model_dump(mode="json"),
        "scorer": args.scorer,
        "dedup": bool(args.dedup),
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

    p_scorers = sub.add_parser("scorers", help="list registered quality scorers")
    p_scorers.set_defaults(func=_cmd_scorers)

    p_presets = sub.add_parser("presets", help="list query-term presets")
    p_presets.set_defaults(func=_cmd_presets)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms (ignored if --preset is set)")
    p_cmp.add_argument("--preset", help=f"named term preset ({', '.join(sorted(PRESETS))})")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument(
        "--scorer",
        default="v1",
        choices=sorted(BATCH_SCORERS),
        help="quality scorer to use",
    )
    p_cmp.add_argument(
        "--dedup",
        action="store_true",
        help="run cross-source deduplication before aggregation",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
