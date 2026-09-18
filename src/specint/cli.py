"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import any_regressed, diff_reports, run_comparison, summarize
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]

# Multilingual seed vocabularies. English stays the baseline; other tags
# reflect the language-hint we send to sources that support it. Additions
# should ship with a fresh fixture + rerun of `specint compare --fixtures`
# to prove they widen license-clean yield.
SEED_TERMS: dict[str, list[str]] = {
    "en": DEFAULT_TERMS,
    "es": ["cocina", "receta"],
    "fr": ["cuisine", "recette"],
    "de": ["kochen", "rezept"],
    "it": ["cucina", "ricetta"],
    "pt": ["culinária", "receita"],
    "nl": ["koken", "recept"],
}


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _resolve_terms(args: argparse.Namespace) -> tuple[list[str], str | None]:
    if args.terms:
        return list(args.terms), args.lang
    if args.lang:
        seed = SEED_TERMS.get(args.lang)
        if not seed:
            raise SystemExit(f"unknown --lang {args.lang!r}; known: {sorted(SEED_TERMS)}")
        return list(seed), args.lang
    return list(DEFAULT_TERMS), None


def _cmd_compare(args: argparse.Namespace) -> int:
    terms, language = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results, language=language)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1;"
            " pass --fixtures for an offline dry run.",
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


def _cmd_compare_diff(args: argparse.Namespace) -> int:
    baseline = json.loads(Path(args.baseline).read_text())
    current = json.loads(Path(args.current).read_text())
    rows = diff_reports(
        baseline,
        current,
        quality_tolerance=args.quality_tolerance,
        record_drop_tolerance=args.record_drop_tolerance,
    )
    payload = {
        "baseline": args.baseline,
        "current": args.current,
        "quality_tolerance": args.quality_tolerance,
        "record_drop_tolerance": args.record_drop_tolerance,
        "rows": [r.to_dict() for r in rows],
        "regressed": any_regressed(rows),
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(summarize(rows))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["regressed"] and args.strict else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms")
    p_cmp.add_argument("--lang", help="BCP-47 seed language (uses SEED_TERMS)")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_diff = sub.add_parser(
        "compare-diff",
        help="regression-check two compare-*.json reports",
    )
    p_diff.add_argument("baseline")
    p_diff.add_argument("current")
    p_diff.add_argument("--quality-tolerance", type=float, default=0.02)
    p_diff.add_argument("--record-drop-tolerance", type=float, default=0.20)
    p_diff.add_argument("--output", help="optional JSON diff report path")
    p_diff.add_argument("--json", action="store_true", help="also print JSON diff")
    p_diff.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any source regressed (use in CI)",
    )
    p_diff.set_defaults(func=_cmd_compare_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
