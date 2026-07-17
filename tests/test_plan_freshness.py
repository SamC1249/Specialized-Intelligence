"""Adversarial-plan freshness nudge.

The Adversarial-Agent role in `AGENTS.md` is required to ship a daily
plan under `docs/plan-YYYY-MM-DD.md`. Without a machine-checkable
freshness signal the file will silently drift for months (as it did
between 2026-06-20 and 2026-07-17 on `main`).

Semantics:

    - Default: emit a `pytest.warns`-visible message but never fail.
      This keeps parallel Coding-Agent branches from becoming
      un-mergeable just because they don't ship a plan.
    - Under `SPECINT_ENFORCE_PLAN_FRESHNESS=1` (set by the scheduled
      `main`-branch CI job): fail if the newest plan is older than
      `MAX_STALENESS_DAYS`.

This is a *convention test*, not a correctness test. Enforcement lives
in CI, not on developer laptops.
"""

from __future__ import annotations

import os
import re
import warnings
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
PLAN_PATTERN = re.compile(r"^plan-(\d{4})-(\d{2})-(\d{2})\.md$")
MAX_STALENESS_DAYS = 30


def _newest_plan_date() -> date | None:
    if not DOCS.exists():
        return None
    dates: list[date] = []
    for p in DOCS.glob("plan-*.md"):
        m = PLAN_PATTERN.match(p.name)
        if not m:
            continue
        try:
            dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue
    return max(dates) if dates else None


def test_at_least_one_dated_plan_exists() -> None:
    newest = _newest_plan_date()
    assert newest is not None, (
        "no docs/plan-YYYY-MM-DD.md files found. The Adversarial-Agent "
        "role requires at least one daily plan; see AGENTS.md."
    )


def test_newest_plan_freshness() -> None:
    newest = _newest_plan_date()
    if newest is None:
        pytest.skip("covered by test_at_least_one_dated_plan_exists")

    today = datetime.now(UTC).date()
    staleness_days = (today - newest).days
    enforce = os.environ.get("SPECINT_ENFORCE_PLAN_FRESHNESS") == "1"
    msg = (
        f"newest docs/plan-*.md is {newest.isoformat()} "
        f"({staleness_days} day(s) old, max={MAX_STALENESS_DAYS})."
    )

    if staleness_days <= MAX_STALENESS_DAYS:
        return

    if enforce:
        pytest.fail(msg + " SPECINT_ENFORCE_PLAN_FRESHNESS=1 → hard fail.")
    warnings.warn(
        msg + " (soft warning; set SPECINT_ENFORCE_PLAN_FRESHNESS=1 to enforce.)", stacklevel=1
    )
