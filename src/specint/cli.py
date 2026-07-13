"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from specint.compare import run_ablation, run_comparison
from specint.quality import deduplicate, score_records
from specint.records import Provenance, SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


class _RefuseLive(Exception):
    """Raised when --fixtures is missing and integration flag is not set."""


def _collect_records(args: argparse.Namespace) -> tuple[SourceQuery, dict[str, list[VideoRecord]]]:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None
    by_source: dict[str, list[VideoRecord]] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        raise _RefuseLive
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
    return query, by_source


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        query, by_source = _collect_records(args)
    except _RefuseLive:
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
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
    try:
        query, by_source = _collect_records(args)
    except _RefuseLive:
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    bundle = run_ablation(query, by_source, notes=args.notes or "")
    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"ablation-{date.today().isoformat()}.json"
    )
    _write_json(out_path, bundle)
    summary = {
        name: {
            "total_mean_quality": preset["total_mean_quality"],
            "total_n_license_clean": preset["total_n_license_clean"],
        }
        for name, preset in bundle["presets"].items()
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _load_records(path: Path) -> list[VideoRecord]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    if not isinstance(data, list):
        raise SystemExit(f"{path}: expected a list of VideoRecord dicts")
    out: list[VideoRecord] = []
    for item in data:
        if "provenance" not in item:
            item["provenance"] = Provenance(extractor="cli.load").model_dump(mode="json")
        out.append(VideoRecord.model_validate(item))
    return out


def _cmd_dedup(args: argparse.Namespace) -> int:
    records = _load_records(Path(args.input))
    scored = score_records(records)
    result = deduplicate(scored, near_threshold=args.threshold)
    payload = {
        "n_input": len(records),
        "n_kept": len(result.kept),
        "n_dropped": result.n_dropped(),
        "kept_ids": [r.id for r in result.kept],
        "absorbed": result.absorbed,
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

    def _add_collect_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--terms", nargs="*", help="search terms")
        sp.add_argument("--only", nargs="*", help="restrict to these source slugs")
        sp.add_argument("--max-results", type=int, default=25)
        sp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
        sp.add_argument("--output", help="output JSON path")
        sp.add_argument("--notes", help="free-form note attached to every row")

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    _add_collect_args(p_cmp)
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="run the quality-weight ablation harness")
    _add_collect_args(p_abl)
    p_abl.set_defaults(func=_cmd_ablate)

    p_dedup = sub.add_parser("dedup", help="deduplicate a JSON list of VideoRecord")
    p_dedup.add_argument("--input", required=True, help="input JSON path (list of VideoRecord)")
    p_dedup.add_argument("--output", help="output JSON path")
    p_dedup.add_argument("--threshold", type=int, default=3, help="SimHash Hamming threshold")
    p_dedup.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
