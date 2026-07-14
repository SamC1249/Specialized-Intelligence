"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import diff_reports, run_comparison, run_matrix
from specint.compare.diff import load_report
from specint.quality import DEFAULT_SCORER, scorer_names
from specint.records import SourceQuery, SourceQuerySuite, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _fixture_by_source_empty(_: SourceQuery) -> dict[str, list[VideoRecord]]:
    return {slug: [] for slug in REGISTRY}


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        loaded: dict[str, list[VideoRecord]] = (
            _load_fixture_records(Path(args.fixtures_dir), query)
            if args.fixtures_dir
            else {slug: [] for slug in REGISTRY}
        )
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = loaded.get(slug, [])
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
            except Exception as exc:
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                records = []
            by_source[slug] = records

    rows = run_comparison(
        query,
        by_source,
        notes=args.notes or "",
        scorer=args.scorer,
        dedup=args.dedup,
    )
    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }

    out_path = _write_report(args.output, payload, "compare")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.output:
        print(f"# wrote {out_path}", file=sys.stderr)
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    suite_path = Path(args.suite)
    suite_data = json.loads(suite_path.read_text())
    suite = SourceQuerySuite.model_validate(suite_data)

    fixtures_root = Path(args.fixtures_dir) if args.fixtures_dir else None

    def by_source_fn(query: SourceQuery) -> dict[str, list[VideoRecord]]:
        if fixtures_root is None:
            return {slug: [] for slug in REGISTRY}
        return _load_fixture_records(fixtures_root, query)

    result = run_matrix(
        suite,
        by_source_fn,
        notes=args.notes or "",
        scorer=args.scorer,
        dedup=args.dedup,
    )
    payload = {
        "suite": suite.model_dump(mode="json"),
        "per_query": [r.model_dump(mode="json") for r in result["per_query"]],
        "per_source": [r.model_dump(mode="json") for r in result["per_source"]],
    }
    out_path = _write_report(args.output, payload, "matrix")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.output:
        print(f"# wrote {out_path}", file=sys.stderr)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    baseline = load_report(args.baseline)
    candidate = load_report(args.candidate)
    rows = diff_reports(baseline, candidate)
    payload = {
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out_path = _write_report(args.output, payload, "diff")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.output:
        print(f"# wrote {out_path}", file=sys.stderr)
    return 0


def _cmd_scorer_compare(args: argparse.Namespace) -> int:
    fixtures_root = Path(args.fixtures_dir) if args.fixtures_dir else None
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    if fixtures_root is None:
        by_source: dict[str, list[VideoRecord]] = {slug: [] for slug in REGISTRY}
    else:
        by_source = _load_fixture_records(fixtures_root, query)

    scorers = args.scorers or scorer_names()
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "scorers": scorers,
        "reports": {},
    }
    for scorer in scorers:
        rows = run_comparison(
            query,
            by_source,
            notes=args.notes or "",
            scorer=scorer,
            dedup=args.dedup,
        )
        payload["reports"][scorer] = [r.model_dump(mode="json") for r in rows]

    out_path = _write_report(args.output, payload, "scorer-compare")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.output:
        print(f"# wrote {out_path}", file=sys.stderr)
    return 0


def _load_fixture_records(fixtures_root: Path, query: SourceQuery) -> dict[str, list[VideoRecord]]:
    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    def _read_json(p: Path) -> Any:
        return json.loads(p.read_text())

    out: dict[str, list[VideoRecord]] = {}
    wm = fixtures_root / "wikimedia/search_pasta.json"
    if wm.exists():
        out["wikimedia"] = WikimediaCommonsSource().parse(_read_json(wm), query)
    ao = fixtures_root / "archive_org/search_cooking.json"
    if ao.exists():
        out["archive_org"] = ArchiveOrgSource().parse(_read_json(ao), query)
    pt = fixtures_root / "peertube/search_cooking.json"
    if pt.exists():
        out["peertube"] = PeerTubeSource().parse(_read_json(pt), query)
    cc = fixtures_root / "common_crawl/recipe_page.html"
    if cc.exists():
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {"html": cc.read_text(), "url": "https://example.test/recipes/garlic-butter-pasta"},
            query,
        )
    for slug in REGISTRY:
        out.setdefault(slug, [])
    return out


def _write_report(output: str | None, payload: dict[str, Any], kind: str) -> Path:
    out_path = (
        Path(output) if output else Path("reports") / f"{kind}-{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return out_path


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
        "--fixtures-dir",
        help="load records from this fixtures root instead of the empty offline default",
    )
    p_cmp.add_argument(
        "--scorer",
        default=DEFAULT_SCORER,
        choices=scorer_names(),
        help="named quality scorer",
    )
    p_cmp.add_argument("--dedup", action="store_true", help="cross-source dedup in __total__")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_mat = sub.add_parser("matrix", help="run a SourceQuerySuite (multi-query benchmark)")
    p_mat.add_argument("--suite", required=True, help="JSON file with a SourceQuerySuite")
    p_mat.add_argument("--fixtures-dir", help="root of tests/fixtures (offline mode)")
    p_mat.add_argument(
        "--scorer",
        default=DEFAULT_SCORER,
        choices=scorer_names(),
        help="named quality scorer",
    )
    p_mat.add_argument("--dedup", action="store_true", help="cross-source dedup in __total__")
    p_mat.add_argument("--output", help="output JSON path")
    p_mat.add_argument("--notes", help="free-form note attached to every row")
    p_mat.set_defaults(func=_cmd_matrix)

    p_diff = sub.add_parser("diff", help="diff two JSON reports")
    p_diff.add_argument("baseline", help="path to baseline report")
    p_diff.add_argument("candidate", help="path to candidate report")
    p_diff.add_argument("--output", help="output JSON path")
    p_diff.set_defaults(func=_cmd_diff)

    p_scm = sub.add_parser("scorer-compare", help="A/B compare all scorers on the same fixture set")
    p_scm.add_argument("--terms", nargs="*", help="search terms")
    p_scm.add_argument("--fixtures-dir", help="root of tests/fixtures (offline mode)")
    p_scm.add_argument(
        "--scorers",
        nargs="*",
        choices=scorer_names(),
        help="which scorers to compare (default: all)",
    )
    p_scm.add_argument("--max-results", type=int, default=25)
    p_scm.add_argument("--dedup", action="store_true")
    p_scm.add_argument("--output", help="output JSON path")
    p_scm.add_argument("--notes", help="free-form note attached to every row")
    p_scm.set_defaults(func=_cmd_scorer_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
