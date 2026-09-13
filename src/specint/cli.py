"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_comparison, run_sweep
from specint.quality import POLICIES, list_policies
from specint.records import SourceQuery
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_policies(_: argparse.Namespace) -> int:
    for name in list_policies():
        p = POLICIES[name]
        print(f"{name}\t{p.notes}")
    return 0


def _load_fixture_records(query: SourceQuery, only: set[str] | None) -> dict[str, list]:
    """Build a `by_source` mapping from the checked-in test fixtures.

    Fixtures mode intentionally uses the same data the tests use so any
    CI-generated sweep is directly comparable to the tests. Keeps CI
    offline while still exercising the harness end-to-end.
    """

    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    fixtures_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

    def _use(slug: str) -> bool:
        return only is None or slug in only

    out: dict[str, list] = {}
    if _use("wikimedia"):
        out["wikimedia"] = WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia" / "search_pasta.json").read_text()),
            query,
        )
    if _use("archive_org"):
        out["archive_org"] = ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org" / "search_cooking.json").read_text()),
            query,
        )
    if _use("peertube"):
        out["peertube"] = PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube" / "search_cooking.json").read_text()),
            query,
        )
    if _use("common_crawl"):
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl" / "recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        )
    return out


def _live_records(query: SourceQuery, only: set[str] | None) -> dict[str, list]:
    by_source: dict[str, list] = {}
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            by_source[slug] = list(cls().search(query))
        except Exception as exc:  # pragma: no cover - integration only
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            by_source[slug] = []
    return by_source


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if args.fixtures:
        by_source = _load_fixture_records(query, only)
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1;"
            " pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        by_source = _live_records(query, only)

    rows = run_comparison(query, by_source, notes=args.notes or "")
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    _write_payload(payload, args.output, prefix="compare")
    return 0


def _cmd_sweep(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    if args.fixtures:
        by_source = _load_fixture_records(query, only)
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1;"
            " pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        by_source = _live_records(query, only)

    selected_policies = None
    if args.policies:
        selected_policies = {name: POLICIES[name] for name in args.policies if name in POLICIES}
        missing = [n for n in args.policies if n not in POLICIES]
        if missing:
            print(f"unknown policy names: {missing}", file=sys.stderr)
            return 2

    payload = run_sweep(query, by_source, policies=selected_policies, notes=args.notes or "")
    _write_payload(payload, args.output, prefix="sweep")
    return 0


def _write_payload(payload: dict[str, Any], output: str | None, prefix: str) -> None:
    out_path = (
        Path(output) if output else Path("reports") / f"{prefix}-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_pol = sub.add_parser("policies", help="list registered quality policies")
    p_pol.set_defaults(func=_cmd_policies)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_swp = sub.add_parser("sweep", help="sweep quality policies across every source")
    p_swp.add_argument("--terms", nargs="*", help="search terms")
    p_swp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_swp.add_argument("--policies", nargs="*", help="restrict to these policy names")
    p_swp.add_argument("--max-results", type=int, default=25)
    p_swp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_swp.add_argument("--output", help="output JSON path")
    p_swp.add_argument("--notes", help="free-form note attached to every row")
    p_swp.set_defaults(func=_cmd_sweep)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
