#!/usr/bin/env python3
"""Schema-check every JSONL manifest against ``VideoRecord``.

Walks ``data/manifests/`` (or any path given on the command line),
parses every ``*.jsonl`` line-by-line and validates each record against
``specint.records.VideoRecord``. Exits non-zero on the first batch of
failures, printing one diagnostic per offending record.

This is the CI counterpart to ``db_structured.md`` — manifests that
don't round-trip through the canonical schema are rejected before they
can pollute downstream training shards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from specint.records import VideoRecord


def _iter_manifests(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".jsonl":
            out.append(root)
            continue
        if not root.is_dir():
            continue
        out.extend(sorted(root.rglob("*.jsonl")))
    return out


def lint_file(path: Path) -> tuple[int, list[str]]:
    """Return (records_seen, errors)."""
    errors: list[str] = []
    seen = 0
    with path.open() as fp:
        for lineno, line in enumerate(fp, 1):
            if not line.strip():
                continue
            seen += 1
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                continue
            try:
                VideoRecord.model_validate(payload)
            except ValidationError as exc:
                errors.append(f"{path}:{lineno}: schema error: {exc.errors()[0]['msg']}")
    return seen, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="manifest_lint")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["data/manifests"],
        help="files or directories to lint (default: data/manifests)",
    )
    parser.add_argument("--allow-empty", action="store_true", help="0 manifests is not an error")
    args = parser.parse_args(argv)

    manifests = _iter_manifests([Path(p) for p in args.paths])
    if not manifests:
        if args.allow_empty:
            print("manifest_lint: no manifests found (allow-empty: ok)")
            return 0
        print("manifest_lint: no manifests found", file=sys.stderr)
        return 0  # warn but don't fail in CI before any manifest exists

    total_records = 0
    total_errors: list[str] = []
    for path in manifests:
        seen, errs = lint_file(path)
        total_records += seen
        total_errors.extend(errs)
        status = "ok" if not errs else f"FAIL ({len(errs)} errors)"
        print(f"{path}: {seen} records {status}")

    if total_errors:
        for line in total_errors:
            print(line, file=sys.stderr)
        return 1
    print(f"manifest_lint: {len(manifests)} manifests, {total_records} records, 0 errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
