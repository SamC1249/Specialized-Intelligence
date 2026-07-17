"""`python -m specint` CLI."""

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
from specint.dedup import deduplicate, group_duplicates
from specint.quality import score_records
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


class _LiveRefused(Exception):
    """Raised when a subcommand needs the network but SPECINT_RUN_INTEGRATION!=1."""


_FIXTURE_ADAPTERS: Mapping[str, tuple[str, str, str]] = {
    "wikimedia": ("wikimedia/search_pasta.json", "json", "parse"),
    "archive_org": ("archive_org/search_cooking.json", "json", "parse"),
    "peertube": ("peertube/search_cooking.json", "json", "parse"),
    "openverse": ("openverse/search_cooking.json", "json", "parse"),
    "common_crawl": ("common_crawl/recipe_page.html", "html", "parse"),
}
_FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


def _load_fixture_records(slug: str, query: SourceQuery) -> list[VideoRecord]:
    if slug not in _FIXTURE_ADAPTERS:
        return []
    rel, kind, _ = _FIXTURE_ADAPTERS[slug]
    fixture_path = _FIXTURE_ROOT / rel
    if not fixture_path.exists():
        return []
    adapter_cls = REGISTRY[slug]
    adapter = adapter_cls()
    if kind == "json":
        raw = json.loads(fixture_path.read_text())
        return list(adapter.parse(raw, query))
    if kind == "html":
        return list(
            adapter.parse(
                {"html": fixture_path.read_text(), "url": "https://example.test/recipe"},
                query,
            )
        )
    return []


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _collect_by_source(
    args: argparse.Namespace, query: SourceQuery
) -> dict[str, list[VideoRecord]]:
    only = set(args.only) if args.only else None
    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = _load_fixture_records(slug, query)
        return by_source
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        raise _LiveRefused()
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            by_source[slug] = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            by_source[slug] = []
    return by_source


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _collect_by_source(args, query)

    if args.dedup:
        scored_all: list[VideoRecord] = []
        for recs in by_source.values():
            scored_all.extend(score_records(recs))
        canonical = deduplicate(scored_all)
        deduped: dict[str, list[VideoRecord]] = {}
        for r in canonical:
            deduped.setdefault(r.source, []).append(r)
        by_source = deduped

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
    _write_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_ablate(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _collect_by_source(args, query)
    payload = run_ablation(query, by_source)
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"ablation-{date.today().isoformat()}.json"
    )
    _write_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    by_source = _collect_by_source(args, query)
    all_records: list[VideoRecord] = []
    for recs in by_source.values():
        all_records.extend(recs)
    groups = group_duplicates(all_records)
    n_dupes = sum(len(g) - 1 for g in groups if len(g) > 1)
    payload = {
        "n_records": len(all_records),
        "n_groups": len(groups),
        "n_duplicates_removed": n_dupes,
        "groups": [
            [
                {
                    "id": r.id,
                    "source": r.source,
                    "title": r.title,
                    "license": r.license.value,
                    "quality_score": r.quality_score,
                }
                for r in g
            ]
            for g in groups
            if len(g) > 1
        ],
    }
    if args.output:
        _write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--terms", nargs="*", help="search terms")
        sp.add_argument("--only", nargs="*", help="restrict to these source slugs")
        sp.add_argument("--max-results", type=int, default=25)
        sp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
        sp.add_argument("--output", help="output JSON path")

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _common(p_cmp)
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument("--dedup", action="store_true", help="apply cross-source dedup first")
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="run weight-config ablation across sources")
    _common(p_abl)
    p_abl.set_defaults(func=_cmd_ablate)

    p_dd = sub.add_parser("dedup", help="report cross-source duplicate groups")
    _common(p_dd)
    p_dd.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except _LiveRefused:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
