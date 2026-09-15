"""`python -m specint` CLI.

Subcommands:

  sources   list registered adapters
  compare   run the fixture / live comparison harness
  ablate    run every source under every scoring profile
  dedup     collapse cross-source duplicates, emit collision matrix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_ablation, run_comparison
from specint.quality.dedup import deduplicate
from specint.quality.metrics import SCORING_PROFILES
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _collect_by_source(
    query: SourceQuery,
    only: set[str] | None,
    fixtures: bool,
) -> tuple[dict[str, list[VideoRecord]], int]:
    """Populate `by_source` for the requested slugs.

    Returns `(by_source, exit_code)`. If `exit_code != 0`, caller should
    short-circuit and return it.
    """
    by_source: dict[str, list[VideoRecord]] = {}
    if fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
        return by_source, 0
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return by_source, 2
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            records = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            records = []
        by_source[slug] = records
    return by_source, 0


def _default_output(prefix: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    return Path("reports") / f"{prefix}-{date.today().isoformat()}.json"


def _dump_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source, rc = _collect_by_source(query, only, args.fixtures)
    if rc:
        return rc

    rows = run_comparison(query, by_source, notes=args.notes or "", profile=args.profile)
    payload = {
        "query": query.model_dump(mode="json"),
        "profile": args.profile,
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out_path = _default_output("compare", args.output)
    _dump_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_ablate(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source, rc = _collect_by_source(query, only, args.fixtures)
    if rc:
        return rc
    profiles = args.profiles or list(SCORING_PROFILES.keys())
    payload = run_ablation(query, by_source, profiles=profiles, notes=args.notes or "")
    out_path = _default_output("ablation", args.output)
    _dump_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source, rc = _collect_by_source(query, only, args.fixtures)
    if rc:
        return rc
    all_records = [r for slug in sorted(by_source) for r in by_source[slug]]
    _, report = deduplicate(all_records)
    payload = {
        "query": query.model_dump(mode="json"),
        "n_input": report.n_input,
        "n_unique": report.n_unique,
        "n_collisions": report.n_collisions,
        "collisions_by_key": report.collisions_by_key,
        "collision_matrix": report.collision_matrix,
        "per_source_unique": report.per_source_unique,
        "notes": args.notes or "",
    }
    out_path = _default_output("dedup", args.output)
    _dump_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--terms", nargs="*", help="search terms")
    sp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    sp.add_argument("--max-results", type=int, default=25)
    sp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    sp.add_argument("--output", help="output JSON path")
    sp.add_argument("--notes", help="free-form note attached to the report")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _add_common(p_cmp)
    p_cmp.add_argument(
        "--profile",
        choices=sorted(SCORING_PROFILES.keys()),
        default=None,
        help="scoring profile (default: balanced)",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="run every source under every scoring profile")
    _add_common(p_abl)
    p_abl.add_argument(
        "--profiles",
        nargs="*",
        choices=sorted(SCORING_PROFILES.keys()),
        help="subset of profiles (default: all)",
    )
    p_abl.set_defaults(func=_cmd_ablate)

    p_dd = sub.add_parser("dedup", help="collapse duplicates across sources")
    _add_common(p_dd)
    p_dd.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
