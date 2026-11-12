"""`python -m specint` CLI.

Subcommands:
  sources   -- list registered sources
  compare   -- run the comparison harness (fixture-driven or live)
  ablate    -- run every quality profile side-by-side (fixture-driven or live)
  dedup     -- run fingerprint dedup over the fixture corpus and print stats

All fixture-driven subcommands are offline and deterministic so they are
safe to run in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_ablation, run_comparison
from specint.dedup import dedup
from specint.fixtures import load_fixture_corpus
from specint.quality import list_profiles, score_records
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _resolve_by_source(
    args: argparse.Namespace, query: SourceQuery, only: set[str] | None
) -> dict[str, list] | None:
    """Return the per-source record lists or None if network access is refused."""
    by_source: dict[str, list] = {}
    if args.fixtures:
        corpus = load_fixture_corpus(query)
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = corpus.get(slug, [])
        return by_source
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return None
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


def _default_output(stem: str) -> Path:
    return Path("reports") / f"{stem}-{date.today().isoformat()}.json"


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source = _resolve_by_source(args, query, only)
    if by_source is None:
        return 2

    rows = run_comparison(query, by_source, notes=args.notes or "", profile=args.profile)
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "profile": args.profile,
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out_path = Path(args.output) if args.output else _default_output("compare")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_ablate(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source = _resolve_by_source(args, query, only)
    if by_source is None:
        return 2
    profiles = args.profiles or list_profiles()
    rows = run_ablation(query, by_source, profiles=profiles, notes=args.notes or "")
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "profiles": profiles,
        "rows": rows,
    }
    out_path = Path(args.output) if args.output else _default_output("ablate")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source = _resolve_by_source(args, query, only)
    if by_source is None:
        return 2
    scored = []
    for records in by_source.values():
        scored.extend(score_records(records, profile=args.profile))
    _, stats = dedup(scored)
    payload = {
        "query": query.model_dump(mode="json"),
        "profile": args.profile,
        "input_count": stats.input_count,
        "output_count": stats.output_count,
        "duplicate_groups": stats.duplicate_groups,
        "dedup_rate": stats.rate,
    }
    out_path = Path(args.output) if args.output else _default_output("dedup")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    def _add_shared(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--terms", nargs="*", help="search terms")
        sp.add_argument("--only", nargs="*", help="restrict to these source slugs")
        sp.add_argument("--max-results", type=int, default=25)
        sp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
        sp.add_argument("--output", help="output JSON path")
        sp.add_argument("--notes", help="free-form note attached to every row")

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _add_shared(p_cmp)
    p_cmp.add_argument("--profile", default="v1", help="quality profile (see `specint ablate`)")
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="run every quality profile side-by-side")
    _add_shared(p_abl)
    p_abl.add_argument(
        "--profiles", nargs="*", help="subset of profiles to run (default: all registered)"
    )
    p_abl.set_defaults(func=_cmd_ablate)

    p_dedup = sub.add_parser("dedup", help="cross-source dedup stats over the corpus")
    _add_shared(p_dedup)
    p_dedup.add_argument("--profile", default="v1", help="quality profile for tie-breaking")
    p_dedup.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
