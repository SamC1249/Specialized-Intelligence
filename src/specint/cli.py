"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_comparison
from specint.domains import DOMAINS, list_domains, terms_for
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

DEFAULT_TERMS = ["cooking", "recipe"]

FixtureLoader = Callable[[Path, SourceQuery], list[VideoRecord]]


def _load_wikimedia(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    path = fixtures_dir / "wikimedia" / "search_pasta.json"
    return WikimediaCommonsSource().parse(json.loads(path.read_text()), query)


def _load_archive(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    path = fixtures_dir / "archive_org" / "search_cooking.json"
    return ArchiveOrgSource().parse(json.loads(path.read_text()), query)


def _load_peertube(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    path = fixtures_dir / "peertube" / "search_cooking.json"
    return PeerTubeSource().parse(json.loads(path.read_text()), query)


def _load_common_crawl(fixtures_dir: Path, query: SourceQuery) -> list[VideoRecord]:
    path = fixtures_dir / "common_crawl" / "recipe_page.html"
    return CommonCrawlRecipeSource().parse(
        {
            "html": path.read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        query,
    )


FIXTURE_LOADERS: dict[str, FixtureLoader] = {
    "wikimedia": _load_wikimedia,
    "archive_org": _load_archive,
    "peertube": _load_peertube,
    "common_crawl": _load_common_crawl,
}


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    baseline = json.loads(Path(args.baseline).read_text())
    candidate = json.loads(Path(args.candidate).read_text())
    b_rows = {r["source"]: r for r in baseline["rows"]}
    c_rows = {r["source"]: r for r in candidate["rows"]}
    sources = sorted(set(b_rows) | set(c_rows))
    deltas: list[dict[str, Any]] = []
    for src in sources:
        b = b_rows.get(src)
        c = c_rows.get(src)
        deltas.append(
            {
                "source": src,
                "baseline_mean_quality": (b or {}).get("mean_quality"),
                "candidate_mean_quality": (c or {}).get("mean_quality"),
                "mean_quality_delta": _safe_delta(
                    (c or {}).get("mean_quality"),
                    (b or {}).get("mean_quality"),
                ),
                "baseline_n_license_clean": (b or {}).get("n_license_clean"),
                "candidate_n_license_clean": (c or {}).get("n_license_clean"),
                "n_license_clean_delta": _safe_delta(
                    (c or {}).get("n_license_clean"),
                    (b or {}).get("n_license_clean"),
                ),
                "baseline_n_records": (b or {}).get("n_records"),
                "candidate_n_records": (c or {}).get("n_records"),
            }
        )
    payload = {
        "baseline_path": args.baseline,
        "candidate_path": args.candidate,
        "deltas": deltas,
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _safe_delta(a: Any, b: Any) -> float | None:
    if a is None or b is None:
        return None
    return float(a) - float(b)


def _cmd_domains(_: argparse.Namespace) -> int:
    for domain in list_domains():
        langs = ",".join(sorted(DOMAINS[domain].keys()))
        print(f"{domain}\tlanguages={langs}")
    return 0


def _resolve_terms(args: argparse.Namespace) -> list[str]:
    if args.terms:
        return list(args.terms)
    if args.domain:
        return terms_for(args.domain, args.language)
    return list(DEFAULT_TERMS)


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = _resolve_terms(args)
    query = SourceQuery(terms=terms, max_results=args.max_results, language=args.language)
    only = set(args.only) if args.only else None
    fixtures_dir = Path(args.fixtures_dir) if args.fixtures_dir else _default_fixtures_dir()

    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        if not fixtures_dir.exists():
            print(f"fixtures dir not found: {fixtures_dir}", file=sys.stderr)
            return 2
        for slug, loader in FIXTURE_LOADERS.items():
            if only and slug not in only:
                continue
            by_source[slug] = loader(fixtures_dir, query)
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
    payload: dict[str, Any] = {
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


def _default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_domains = sub.add_parser("domains", help="list registered domain profiles")
    p_domains.set_defaults(func=_cmd_domains)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms (overrides --domain)")
    p_cmp.add_argument("--domain", choices=list_domains(), help="use a canonical domain profile")
    p_cmp.add_argument("--language", help="BCP-47 language hint (used by domain profiles)")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument(
        "--fixtures",
        action="store_true",
        help="offline mode — actually parse tests/fixtures/*",
    )
    p_cmp.add_argument("--fixtures-dir", help="override path to tests/fixtures")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_diff = sub.add_parser(
        "compare-diff",
        help="diff two comparison JSON reports (candidate - baseline)",
    )
    p_diff.add_argument("--baseline", required=True, help="baseline report JSON")
    p_diff.add_argument("--candidate", required=True, help="candidate report JSON")
    p_diff.add_argument("--output", help="output JSON path")
    p_diff.set_defaults(func=_cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
