"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_comparison
from specint.quality import DurationProfile
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]
FIXTURE_LOADERS: dict[str, tuple[str, str]] = {
    "wikimedia": ("wikimedia/search_pasta.json", "json"),
    "archive_org": ("archive_org/search_cooking.json", "json"),
    "peertube": ("peertube/search_cooking.json", "json"),
    "common_crawl": ("common_crawl/recipe_page.html", "html"),
    "youtube_cc": ("youtube_cc/search_cooking.json", "json"),
}


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _load_fixture_records(slug: str, fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    if slug not in FIXTURE_LOADERS:
        return []
    rel, kind = FIXTURE_LOADERS[slug]
    path = fixtures_dir / rel
    if not path.exists():
        return []
    cls = REGISTRY[slug]
    src = cls()
    if kind == "json":
        return src.parse(json.loads(path.read_text()), query)
    if kind == "html":
        return src.parse(
            {"html": path.read_text(), "url": "https://example.test/recipes/fixture"}, query
        )
    return []


def _collect_by_source(
    args: argparse.Namespace, query: SourceQuery
) -> dict[str, list[VideoRecord]]:
    only = set(args.only) if args.only else None
    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else Path("tests/fixtures")
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = _load_fixture_records(slug, fixtures_dir, query)
        return by_source
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        raise SystemExit(2)
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


def _profile_from_str(value: str) -> DurationProfile:
    return DurationProfile(value)


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _collect_by_source(args, query)

    rows = run_comparison(
        query,
        by_source,
        notes=args.notes or "",
        dedup=not args.no_dedup,
        duration_profile=_profile_from_str(args.duration_profile),
    )
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "duration_profile": args.duration_profile,
        "dedup": not args.no_dedup,
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


def _cmd_ablate_duration(args: argparse.Namespace) -> int:
    """Run both duration profiles against the same corpus and emit a diff."""
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _collect_by_source(args, query)

    per_profile: dict[str, dict[str, dict[str, float]]] = {}
    for profile in DurationProfile:
        rows = run_comparison(query, by_source, dedup=not args.no_dedup, duration_profile=profile)
        per_profile[profile.value] = {
            row.source: {
                "mean_quality": row.mean_quality,
                "p50_quality": row.p50_quality,
                "p90_quality": row.p90_quality,
                "n_records": row.n_records,
                "n_duplicates_removed": row.n_duplicates_removed,
            }
            for row in rows
        }

    sources = sorted({s for prof in per_profile.values() for s in prof})
    delta: dict[str, dict[str, float]] = {}
    for src in sources:
        short = per_profile["short_form"].get(src, {})
        long_ = per_profile["long_form"].get(src, {})
        delta[src] = {
            "delta_mean_quality": (long_.get("mean_quality", 0.0) - short.get("mean_quality", 0.0)),
        }

    payload = {
        "query": query.model_dump(mode="json"),
        "per_profile": per_profile,
        "delta_long_minus_short": delta,
    }
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"duration-ablation-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _add_shared_compare_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--terms", nargs="*", help="search terms")
    parser.add_argument("--only", nargs="*", help="restrict to these source slugs")
    parser.add_argument("--max-results", type=int, default=25)
    parser.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    parser.add_argument("--fixtures-dir", help="override the fixtures directory")
    parser.add_argument("--output", help="output JSON path")
    parser.add_argument("--notes", help="free-form note attached to every row")
    parser.add_argument("--no-dedup", action="store_true", help="skip cross-source deduplication")
    parser.add_argument(
        "--duration-profile",
        choices=[p.value for p in DurationProfile],
        default=DurationProfile.SHORT_FORM.value,
        help="duration-scoring profile (see specint.quality.DurationProfile)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _add_shared_compare_args(p_cmp)
    p_cmp.set_defaults(func=_cmd_compare)

    p_ablate = sub.add_parser(
        "ablate-duration",
        help="run both duration profiles and emit a delta report",
    )
    _add_shared_compare_args(p_ablate)
    p_ablate.set_defaults(func=_cmd_ablate_duration)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
