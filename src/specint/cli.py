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
from specint.estimate import estimate_yield
from specint.quality import PROFILES
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

DEFAULT_TERMS = ["cooking", "recipe"]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _load_fixture_records(fixtures_dir: Path, query: SourceQuery) -> dict[str, list[VideoRecord]]:
    """Load the shipped per-source fixtures and parse them via each adapter."""
    by_source: dict[str, list[VideoRecord]] = {slug: [] for slug in REGISTRY}
    wiki_dir = fixtures_dir / "wikimedia"
    if wiki_dir.is_dir():
        parsed: list[VideoRecord] = []
        for p in sorted(wiki_dir.glob("*.json")):
            parsed.extend(WikimediaCommonsSource().parse(json.loads(p.read_text()), query))
        by_source["wikimedia"] = parsed
    ia_dir = fixtures_dir / "archive_org"
    if ia_dir.is_dir():
        parsed = []
        for p in sorted(ia_dir.glob("*.json")):
            parsed.extend(ArchiveOrgSource().parse(json.loads(p.read_text()), query))
        by_source["archive_org"] = parsed
    pt_dir = fixtures_dir / "peertube"
    if pt_dir.is_dir():
        parsed = []
        for p in sorted(pt_dir.glob("*.json")):
            parsed.extend(PeerTubeSource().parse(json.loads(p.read_text()), query))
        by_source["peertube"] = parsed
    cc_dir = fixtures_dir / "common_crawl"
    if cc_dir.is_dir():
        parsed = []
        for p in sorted(cc_dir.glob("*.html")):
            parsed.extend(
                CommonCrawlRecipeSource().parse(
                    {"html": p.read_text(), "url": f"https://example.test/{p.stem}"},
                    query,
                )
            )
        by_source["common_crawl"] = parsed
    return by_source


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if args.profile not in PROFILES:
        print(
            f"unknown profile {args.profile!r}; choose from {sorted(PROFILES)}",
            file=sys.stderr,
        )
        return 2

    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else DEFAULT_FIXTURES_DIR
        loaded = _load_fixture_records(fixtures_dir, query)
        for slug, records in loaded.items():
            if only and slug not in only:
                continue
            by_source[slug] = records
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
        profile=args.profile,
        dedup=args.dedup,
    )
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "profile": args.profile,
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


def _cmd_estimate(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    if not args.fixtures and os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "estimate refuses live network without SPECINT_RUN_INTEGRATION=1; pass --fixtures.",
            file=sys.stderr,
        )
        return 2

    if args.fixtures:
        fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else DEFAULT_FIXTURES_DIR
        by_source = _load_fixture_records(fixtures_dir, query)
    else:  # pragma: no cover - integration only
        by_source = {slug: list(cls().search(query)) for slug, cls in REGISTRY.items()}

    est = estimate_yield(by_source, projected_pages=max(1, args.projected_pages))
    payload = est.model_dump(mode="json")
    payload["query"] = query.model_dump(mode="json")
    payload["projected_pages"] = args.projected_pages
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
    p_cmp.add_argument(
        "--fixtures-dir", help="override fixtures directory (default: repo tests/fixtures)"
    )
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument(
        "--profile",
        default="v1",
        choices=sorted(PROFILES.keys()),
        help="quality-scoring profile (v1: baseline, v2: procedural-density)",
    )
    p_cmp.add_argument(
        "--dedup", action="store_true", help="apply cross-source deduplicator before aggregating"
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_est = sub.add_parser("estimate", help="metadata-only yield estimator")
    p_est.add_argument("--terms", nargs="*", help="search terms")
    p_est.add_argument("--max-results", type=int, default=25)
    p_est.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_est.add_argument("--fixtures-dir", help="override fixtures directory")
    p_est.add_argument(
        "--projected-pages",
        type=int,
        default=1,
        help="linear extrapolation multiplier over the sampled page (default: 1 = no extrapolation)",
    )
    p_est.add_argument("--output", help="output JSON path")
    p_est.set_defaults(func=_cmd_estimate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
