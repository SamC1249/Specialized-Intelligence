#!/usr/bin/env python3
"""Enforce AGENTS.md §Daily Loop: every `docs/plan-YYYY-MM-DD.md` must have a
matching dated entry in `plan.md`, and `plan.md` entries must be in
reverse-chronological order.

Runs as a pre-commit hook and as a CI step. Exits non-zero with a human
message on the first violation.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from itertools import pairwise
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
PLAN_MD = REPO / "plan.md"

PLAN_FILE_RE = re.compile(r"^plan-(\d{4}-\d{2}-\d{2})\.md$")
ENTRY_LINE_RE = re.compile(r"^-\s*\[[^\]]+@\s*(?P<date>\d{4}-\d{2}-\d{2})T[\d:]+Z\]")


def _plan_files() -> list[date]:
    dates: list[date] = []
    for p in sorted(DOCS.glob("plan-*.md")):
        m = PLAN_FILE_RE.match(p.name)
        if not m:
            continue
        try:
            dates.append(date.fromisoformat(m.group(1)))
        except ValueError:
            print(f"error: bad date in {p.name}", file=sys.stderr)
            return []
    return dates


def _plan_md_entries() -> list[date]:
    if not PLAN_MD.exists():
        return []
    out: list[date] = []
    for line in PLAN_MD.read_text().splitlines():
        m = ENTRY_LINE_RE.match(line.strip())
        if not m:
            continue
        try:
            out.append(date.fromisoformat(m.group("date")))
        except ValueError:
            continue
    return out


def _check_reverse_chronological(entries: list[date]) -> str | None:
    for prev, curr in pairwise(entries):
        if curr > prev:
            return (
                "plan.md is not reverse-chronological: "
                f"{curr.isoformat()} appears below {prev.isoformat()}"
            )
    return None


def main() -> int:
    file_dates = set(_plan_files())
    entries = _plan_md_entries()
    entry_dates = set(entries)

    missing = sorted(file_dates - entry_dates)
    orphan = sorted(entry_dates - file_dates)

    problems: list[str] = []
    for d in missing:
        problems.append(f"docs/plan-{d.isoformat()}.md has no matching dated line in plan.md")
    for d in orphan:
        problems.append(
            f"plan.md references {d.isoformat()} but docs/plan-{d.isoformat()}.md is missing"
        )
    bad_order = _check_reverse_chronological(entries)
    if bad_order:
        problems.append(bad_order)

    if problems:
        for p in problems:
            print(f"plan-entry: {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
