"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_full_report
from specint.dedupe import dedupe as dedupe_records
from specint.dedupe import fingerprint
from specint.dedupe import overlap as overlap_of
from specint.quality import score_records
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]

FIXTURES_ROOT = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


class _LiveNetworkRefused(RuntimeError):
    """Raised when a live-network command runs without the opt-in env var."""


# Map source slug -> (fixture path relative to FIXTURES_ROOT, raw-mode).
# raw-mode "json" means parsed JSON is passed directly to source.parse().
# raw-mode "html" wraps html into the {"html": ..., "url": ...} shape
# expected by CommonCrawlRecipeSource.parse().
_FIXTURE_MAP: dict[str, tuple[str, str]] = {
    "wikimedia": ("wikimedia/search_pasta.json", "json"),
    "archive_org": ("archive_org/search_cooking.json", "json"),
    "peertube": ("peertube/search_cooking.json", "json"),
    "common_crawl": ("common_crawl/recipe_page.html", "html"),
    "youtube": ("youtube/videos_list.json", "json"),
}


def _load_fixture_records(slug: str, query: SourceQuery) -> list[VideoRecord]:
    entry = _FIXTURE_MAP.get(slug)
    if entry is None:
        return []
    rel, mode = entry
    path = FIXTURES_ROOT / rel
    if not path.exists():
        return []
    source_cls = REGISTRY[slug]
    if mode == "json":
        raw = json.loads(path.read_text())
    elif mode == "html":
        raw = {
            "html": path.read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        }
    else:
        return []
    return list(source_cls().parse(raw, query))


def _collect_records(
    query: SourceQuery,
    fixtures: bool,
    only: set[str] | None,
) -> dict[str, list[VideoRecord]]:
    by_source: dict[str, list[VideoRecord]] = {}
    if fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = _load_fixture_records(slug, query)
        return by_source

    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        raise _LiveNetworkRefused(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1;"
            " pass --fixtures for an offline dry run."
        )

    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            by_source[slug] = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration path
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            by_source[slug] = []
    return by_source


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(
        terms=terms,
        max_results=args.max_results,
        language=args.language,
    )
    only = set(args.only) if args.only else None
    try:
        by_source = _collect_records(query, fixtures=args.fixtures, only=only)
    except _LiveNetworkRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = run_full_report(
        query,
        by_source,
        notes=args.notes or "",
        with_dedupe=args.dedupe,
    )

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
    only = set(args.only) if args.only else None
    try:
        by_source = _collect_records(query, fixtures=args.fixtures, only=only)
    except _LiveNetworkRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    scored_by_source = {
        source: score_records(records, query) for source, records in by_source.items()
    }
    flat: list[VideoRecord] = [rec for recs in scored_by_source.values() for rec in recs]
    deduped = dedupe_records(flat)
    payload = {
        "query": query.model_dump(mode="json"),
        "n_records": len(flat),
        "n_after_dedupe": len(deduped),
        "overlap": overlap_of(scored_by_source),
        "fingerprints": sorted({fingerprint(r) for r in flat}),
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
    p_cmp.add_argument("--language", help="BCP-47 language filter fed into quality scoring")
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--dedupe", action="store_true", help="include dedupe/overlap block")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_dedupe = sub.add_parser("dedupe", help="report cross-source overlap and dedupe stats")
    p_dedupe.add_argument("--terms", nargs="*", help="search terms")
    p_dedupe.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_dedupe.add_argument("--max-results", type=int, default=25)
    p_dedupe.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_dedupe.add_argument("--output", help="output JSON path")
    p_dedupe.set_defaults(func=_cmd_dedupe)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
