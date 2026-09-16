#!/usr/bin/env python3
"""Pre-commit hook: validate every `reports/*.json` file.

Ensures each report is valid JSON and contains the expected top-level
keys (`query`, `rows`). Cheap invariant that stops a mangled baseline
from being committed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_TOP_LEVEL_KEYS = {"query", "rows"}


def validate(path: Path) -> list[str]:
    errs: list[str] = []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path}: top-level must be a JSON object"]

    if path.name.startswith(("baseline-", "compare-", "ci-compare", "ci-regression")):
        # regression reports have their own schema; only enforce keys on comparisons
        if path.name.startswith("ci-regression"):
            for key in ("baseline_path", "ok", "deltas"):
                if key not in payload:
                    errs.append(f"{path}: missing regression key {key!r}")
            return errs
        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in payload:
                errs.append(f"{path}: missing key {key!r}")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            errs.append(f"{path}: 'rows' must be a list")
        else:
            for i, row in enumerate(rows):
                if not isinstance(row, dict) or "source" not in row:
                    errs.append(f"{path}: rows[{i}] missing 'source'")
    return errs


def main(argv: list[str]) -> int:
    paths: list[Path] = []
    paths = [Path(p) for p in argv[1:]] if len(argv) > 1 else sorted(Path("reports").glob("*.json"))
    if not paths:
        return 0

    errs: list[str] = []
    for p in paths:
        if not p.exists() or p.is_dir():
            continue
        errs.extend(validate(p))

    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
