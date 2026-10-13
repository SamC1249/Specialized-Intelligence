"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint._git import short_sha
from specint.compare import run_comparison, run_fixture_harness, serialise
from specint.records import SourceQuery, VideoRecord
from specint.sources import REGISTRY

DEFAULT_TERMS = ["cooking", "recipe"]
FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _doctor_check_adapter(slug: str) -> tuple[bool, str]:
    """Confirm an adapter imports and can be instantiated without I/O."""
    cls = REGISTRY.get(slug)
    if cls is None:
        return False, f"not registered"
    try:
        importlib.import_module(cls.__module__)
        inst = cls()
        _ = inst.slug  # noqa: F841
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"import/instantiate failed: {exc}"
    return True, "ok"


def _doctor_check_fixtures(slug: str) -> tuple[int, int, list[str]]:
    """Parse every fixture under tests/fixtures/<slug>/ and validate.

    Returns (ok_count, total_count, errors).
    """
    cls = REGISTRY.get(slug)
    if cls is None:
        return 0, 0, [f"no adapter registered for {slug}"]
    folder = FIXTURES_ROOT / slug
    if not folder.exists():
        return 0, 0, [f"no fixture folder at {folder}"]
    inst = cls()
    query = SourceQuery(terms=["doctor"], max_results=1)
    ok, total, errors = 0, 0, []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        total += 1
        try:
            if path.suffix == ".json":
                raw: object = json.loads(path.read_text())
            elif path.suffix in {".html", ".htm"}:
                raw = {"html": path.read_text(), "url": "https://doctor.test/" + path.stem}
            else:
                continue
            records = inst.parse(raw, query)
            for r in records:
                if not isinstance(r, VideoRecord):
                    raise TypeError(f"parse returned non-VideoRecord: {type(r).__name__}")
            ok += 1
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
    return ok, total, errors


def _cmd_doctor(args: argparse.Namespace) -> int:
    print(f"extractor_git: {short_sha()}")
    print(f"fixtures_root: {FIXTURES_ROOT}")
    print(f"registered sources: {len(REGISTRY)}")
    hard_fail = False
    rows: list[tuple[str, str, str]] = []
    for slug in sorted(REGISTRY):
        ok_adapter, adapter_msg = _doctor_check_adapter(slug)
        ok_fx, total_fx, fx_errors = _doctor_check_fixtures(slug)
        status = "OK" if (ok_adapter and not fx_errors) else "FAIL"
        if status == "FAIL":
            hard_fail = True
        rows.append((slug, status, f"adapter={adapter_msg} fixtures={ok_fx}/{total_fx}"))
        for err in fx_errors:
            rows.append((slug, "  ·", err))
    width = max(len(r[0]) for r in rows) if rows else 0
    for slug, status, detail in rows:
        print(f"{slug.ljust(width)}  {status:<4}  {detail}")
    if args.json:
        payload = {
            "extractor_git": short_sha(),
            "sources": {slug: {"status": status, "detail": detail} for slug, status, detail in rows},
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if hard_fail else 0


def _cmd_compare(args: argparse.Namespace) -> int:
    terms = args.terms or DEFAULT_TERMS
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        # Delegates to the shared fixture harness so CLI output, the regression
        # gate, and the baseline-generation script can never drift apart.
        fx_query, fx_rows = run_fixture_harness(terms=terms, notes=args.notes or "fixture-cli")
        payload = serialise(fx_query, fx_rows)
        out_path = (
            Path(args.output)
            if args.output
            else Path("reports") / f"compare-{date.today().isoformat()}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
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
    p_cmp.set_defaults(func=_cmd_compare)

    p_doc = sub.add_parser(
        "doctor",
        help="validate adapters import, fixtures parse, and resolved extractor_git",
    )
    p_doc.add_argument("--json", action="store_true", help="emit a JSON summary at the end")
    p_doc.set_defaults(func=_cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
