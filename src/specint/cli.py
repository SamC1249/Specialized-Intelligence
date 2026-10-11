"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_comparison
from specint.compare.fixtures import FIXTURE_LOADERS
from specint.quality.language import seed_terms
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_LANGUAGE = "en"


def _resolve_terms(args: argparse.Namespace) -> list[str]:
    if args.terms:
        return list(args.terms)
    return seed_terms(args.language)


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results, language=args.language)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            loader = FIXTURE_LOADERS.get(slug)
            by_source[slug] = list(loader(query)) if loader else []
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
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


_DIFF_METRICS: tuple[str, ...] = (
    "n_records",
    "n_license_clean",
    "license_clean_hours",
    "total_duration_s",
    "mean_quality",
    "p50_quality",
    "p90_quality",
    "top10_mean_quality",
    "n_with_steps",
    "n_duplicates_dropped",
)


def _rows_by_source(payload: dict) -> dict[str, dict]:
    return {row["source"]: row for row in payload.get("rows", [])}


def _cmd_diff(args: argparse.Namespace) -> int:
    base = json.loads(Path(args.base).read_text())
    new = json.loads(Path(args.new).read_text())
    base_by = _rows_by_source(base)
    new_by = _rows_by_source(new)
    sources = sorted(set(base_by) | set(new_by))

    diffs: list[dict] = []
    for src in sources:
        b = base_by.get(src, {})
        n = new_by.get(src, {})
        row: dict = {"source": src}
        for metric in _DIFF_METRICS:
            bv = b.get(metric) or 0
            nv = n.get(metric) or 0
            try:
                row[metric] = {"base": bv, "new": nv, "delta": nv - bv}
            except TypeError:
                row[metric] = {"base": bv, "new": nv, "delta": None}
        diffs.append(row)

    out = {
        "base": str(args.base),
        "new": str(args.new),
        "metrics": list(_DIFF_METRICS),
        "diffs": diffs,
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def _cmd_languages(_: argparse.Namespace) -> int:
    for tag in sorted(seed_terms_registry()):
        print(f"{tag}\t{', '.join(seed_terms(tag))}")
    return 0


def seed_terms_registry() -> list[str]:
    from specint.quality.language import all_seed_languages

    return list(all_seed_languages())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_langs = sub.add_parser("languages", help="list multilingual seed term sets")
    p_langs.set_defaults(func=_cmd_languages)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms (override language seed)")
    p_cmp.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="BCP-47 language tag; selects the default seed term set",
    )
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (loads fixtures)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_diff = sub.add_parser("diff", help="diff two compare JSON reports")
    p_diff.add_argument("base", help="baseline report JSON path")
    p_diff.add_argument("new", help="new report JSON path")
    p_diff.add_argument("--output", help="optional output JSON path")
    p_diff.set_defaults(func=_cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
