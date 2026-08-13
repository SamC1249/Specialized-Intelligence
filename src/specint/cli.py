"""`python -m specint` CLI.

Subcommands:
  - `sources` — list registered adapters.
  - `compare` — run the comparison harness, optionally with dedupe /
    language filter / multilingual seed terms. `--fixtures` loads the
    checked-in JSON/HTML fixtures under `tests/fixtures/` so CI can
    produce a real report without network access.
  - `dedupe` — inspection subcommand: prints the cross-source overlap
    matrix and the collapsed record count for the fixture universe.
  - `ablate` — runs the weight-ablation harness across `baseline`,
    `license_heavy`, and `procedural_heavy` weight vectors and emits a
    matrix report.

Live network hits are gated behind `SPECINT_RUN_INTEGRATION=1`; every
other invocation must pass `--fixtures` explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import build_report, run_ablation, run_comparison
from specint.compare.ablation import ablation_matrix
from specint.dedupe import dedupe_by_source, overlap
from specint.quality import all_seed_terms
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

DEFAULT_TERMS = ["cooking", "recipe"]

# Fixture layout is stable — see `tests/fixtures/`. We resolve
# relative to the repo root so `python -m specint compare --fixtures`
# works from any cwd inside the workspace.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_ROOT = _REPO_ROOT / "tests" / "fixtures"


def _load_fixture_records(query: SourceQuery) -> dict[str, list[VideoRecord]]:
    """Load every checked-in fixture into records grouped by source slug.

    This is the one place that knows the on-disk fixture layout. If
    fixtures are absent (e.g. running from an install where tests were
    stripped), each slug returns an empty list.
    """
    out: dict[str, list[VideoRecord]] = {slug: [] for slug in REGISTRY}
    root = _FIXTURE_ROOT
    if not root.exists():
        return out

    wm_path = root / "wikimedia" / "search_pasta.json"
    if wm_path.exists():
        raw = json.loads(wm_path.read_text())
        out["wikimedia"] = WikimediaCommonsSource().parse(raw, query)

    ia_path = root / "archive_org" / "search_cooking.json"
    if ia_path.exists():
        raw = json.loads(ia_path.read_text())
        out["archive_org"] = ArchiveOrgSource().parse(raw, query)

    pt_path = root / "peertube" / "search_cooking.json"
    if pt_path.exists():
        raw = json.loads(pt_path.read_text())
        out["peertube"] = PeerTubeSource().parse(raw, query)

    cc_path = root / "common_crawl" / "recipe_page.html"
    if cc_path.exists():
        out["common_crawl"] = CommonCrawlRecipeSource().parse(
            {
                "html": cc_path.read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        )
    return out


def _live_search(
    query: SourceQuery, only: set[str] | None
) -> dict[str, list[VideoRecord]]:  # pragma: no cover - integration only
    out: dict[str, list[VideoRecord]] = {}
    for slug, cls in REGISTRY.items():
        if only and slug not in only:
            continue
        try:
            records = list(cls().search(query))
        except Exception as exc:
            print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
            records = []
        out[slug] = records
    return out


def _terms_for_run(args: argparse.Namespace) -> list[str]:
    if args.multilingual:
        return list(all_seed_terms())
    return args.terms or DEFAULT_TERMS


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = _terms_for_run(args)
    query = SourceQuery(
        terms=terms,
        max_results=args.max_results,
        language=args.language,
    )
    only = set(args.only) if args.only else None

    by_source: Mapping[str, list[VideoRecord]]
    if args.fixtures:
        loaded = _load_fixture_records(query)
        by_source = {
            slug: recs for slug, recs in loaded.items() if not only or slug in only
        }
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        by_source = _live_search(query, only)

    payload = build_report(
        query,
        by_source,
        notes=args.notes or "",
        dedupe_enabled=args.dedupe,
    )
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"compare-{date.today().isoformat()}.json"
    )
    _write_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_dedupe(args: argparse.Namespace) -> int:
    query = SourceQuery(terms=DEFAULT_TERMS, max_results=args.max_results)
    by_source = _load_fixture_records(query)
    overlap_payload = overlap(by_source)
    _, total_collapsed = dedupe_by_source(by_source)
    payload = {
        "overlap": overlap_payload,
        "total_collapsed": total_collapsed,
    }
    if args.output:
        _write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_ablate(args: argparse.Namespace) -> int:
    query = SourceQuery(
        terms=_terms_for_run(args),
        max_results=args.max_results,
        language=args.language,
    )
    if args.fixtures:
        by_source = _load_fixture_records(query)
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:  # pragma: no cover - integration only
        by_source = _live_search(query, None)

    runs = run_ablation(query, by_source)
    payload = ablation_matrix(runs)
    payload["query"] = query.model_dump(mode="json")
    payload["per_variant"] = [
        {
            "variant": r.variant,
            "rows": [row.model_dump(mode="json") for row in r.rows],
        }
        for r in runs
    ]

    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"ablate-{date.today().isoformat()}.json"
    )
    _write_json(out_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms (ignored if --multilingual)")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument("--dedupe", action="store_true", help="cross-source deduplication")
    p_cmp.add_argument(
        "--multilingual",
        action="store_true",
        help="union seed terms across every supported language",
    )
    p_cmp.add_argument(
        "--language",
        help="ISO 639-1 target language; used as a soft language_match filter",
    )
    p_cmp.set_defaults(func=_cmd_compare)

    p_dd = sub.add_parser("dedupe", help="print cross-source overlap on fixtures")
    p_dd.add_argument("--max-results", type=int, default=25)
    p_dd.add_argument("--output", help="output JSON path")
    p_dd.set_defaults(func=_cmd_dedupe)

    p_ab = sub.add_parser("ablate", help="run weight-vector ablation harness")
    p_ab.add_argument("--terms", nargs="*", help="search terms")
    p_ab.add_argument("--fixtures", action="store_true")
    p_ab.add_argument("--max-results", type=int, default=25)
    p_ab.add_argument("--output", help="output JSON path")
    p_ab.add_argument("--multilingual", action="store_true")
    p_ab.add_argument("--language", help="ISO 639-1 target language")
    p_ab.set_defaults(func=_cmd_ablate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
