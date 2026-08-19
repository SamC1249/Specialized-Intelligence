"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import compare_runs, run_comparison
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _fixture_root() -> Path:
    override = os.environ.get("SPECINT_FIXTURE_ROOT")
    if override:
        return Path(override)
    candidate = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"
    if candidate.exists():
        return candidate
    return Path.cwd() / "tests" / "fixtures"


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _load_fixture_records(query: SourceQuery, only: set[str] | None = None) -> dict[str, list]:
    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikidata import WikidataSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    root = _fixture_root()
    parsed: dict[str, list] = {}
    fixtures = {
        "wikimedia": (WikimediaCommonsSource(), "wikimedia/search_pasta.json", "json"),
        "archive_org": (ArchiveOrgSource(), "archive_org/search_cooking.json", "json"),
        "peertube": (PeerTubeSource(), "peertube/search_cooking.json", "json"),
        "wikidata": (WikidataSource(), "wikidata/sparql_cooking.json", "json"),
        "common_crawl": (CommonCrawlRecipeSource(), "common_crawl/recipe_page.html", "cc"),
    }
    for slug, (adapter, rel, kind) in fixtures.items():
        if only and slug not in only:
            continue
        path = root / rel
        if not path.exists():
            parsed[slug] = []
            continue
        if kind == "json":
            parsed[slug] = adapter.parse(json.loads(path.read_text()), query)
        else:
            parsed[slug] = adapter.parse(
                {
                    "html": path.read_text(),
                    "url": "https://example.test/recipes/garlic-butter-pasta",
                },
                query,
            )
    return parsed


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if args.fixtures:
        by_source = _load_fixture_records(query, only=only)
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        by_source = {}
        for slug, cls in REGISTRY.items():
            if only and slug not in only:
                continue
            try:
                by_source[slug] = list(cls().search(query))
            except Exception as exc:  # pragma: no cover - integration only
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                by_source[slug] = []

    rows = run_comparison(query, by_source, notes=args.notes or "", scorer_profile=args.profile)
    payload = {
        "query": query.model_dump(mode="json"),
        "scorer_profile": args.profile,
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


def _cmd_bench(args: argparse.Namespace) -> int:
    """Run both scorer profiles on the fixture set and report a Pareto delta.

    Exit codes:
      0 = v2 dominates or ties v1 (safe to keep)
      3 = v2 is dominated by v1 (regression)
      4 = v2 has mixed dominance vs v1 (needs human review)
    """
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _load_fixture_records(query)

    a_rows = run_comparison(query, by_source, notes="bench-v1", scorer_profile="v1")
    b_rows = run_comparison(query, by_source, notes="bench-v2", scorer_profile="v2_procedural")
    delta = compare_runs(a_rows, b_rows)

    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "runs": {
            "v1": [r.model_dump(mode="json") for r in a_rows],
            "v2_procedural": [r.model_dump(mode="json") for r in b_rows],
        },
        "delta": delta.as_dict(),
    }
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"bench-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))

    if delta.verdict in {"dominates", "tie"}:
        return 0
    if delta.verdict == "dominated":
        return 3
    return 4


def _cmd_dedup(args: argparse.Namespace) -> int:
    from specint.quality import dedupe

    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _load_fixture_records(query)
    all_records = [r for group in by_source.values() for r in group]
    report = dedupe(all_records)
    payload = {
        "n_input": report.n_input,
        "n_unique": report.n_unique,
        "n_duplicates": len(report.duplicates),
        "pairs_by_signal": report.pairs_by_signal,
        "clusters": [[r.id for r in cluster] for cluster in report.clusters if len(cluster) > 1],
    }
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
        "--profile", default="v1", choices=("v1", "v2_procedural"), help="scorer profile"
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_bench = sub.add_parser(
        "bench", help="run every scorer profile on fixtures and Pareto-compare them"
    )
    p_bench.add_argument("--terms", nargs="*", help="search terms")
    p_bench.add_argument("--max-results", type=int, default=25)
    p_bench.add_argument("--output", help="output JSON path")
    p_bench.set_defaults(func=_cmd_bench)

    p_dd = sub.add_parser("dedup-report", help="report dedup clusters across all fixture sources")
    p_dd.add_argument("--terms", nargs="*", help="search terms")
    p_dd.add_argument("--max-results", type=int, default=25)
    p_dd.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
