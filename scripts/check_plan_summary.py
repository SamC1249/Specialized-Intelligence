#!/usr/bin/env python3
"""Pre-commit / CI guard: whenever a `docs/plan-YYYY-MM-DD.md` file is
staged (added or modified), `plan.md` must also contain a corresponding
dated summary line.

Rationale: AGENTS.md §5 says each Coding-Agent / Adversarial-Agent day
appends a one-line summary to `plan.md`. Prior to this hook that step
was easy to forget; the guard makes forgetting it a red build.

Invocation modes:

  * Pre-commit (default): the pre-commit framework passes the list of
    files being changed as positional args. We only care about
    `docs/plan-*.md`.
  * Manual audit: `python scripts/check_plan_summary.py --all` scans
    every `docs/plan-*.md` and checks that plan.md references its date.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_LOG = REPO_ROOT / "plan.md"
PLAN_DIR = REPO_ROOT / "docs"
PLAN_RE = re.compile(r"^docs/plan-(\d{4}-\d{2}-\d{2})\.md$")


def _date_in_plan_log(date_str: str, log_text: str) -> bool:
    return date_str in log_text


def _dates_from_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        m = PLAN_RE.match(p)
        if m:
            out.append(m.group(1))
    return out


def main(argv: list[str]) -> int:
    if not PLAN_LOG.exists():
        print("plan.md missing at repo root", file=sys.stderr)
        return 1
    log_text = PLAN_LOG.read_text()

    if argv and argv[0] == "--all":
        dates = sorted({p.stem.replace("plan-", "") for p in PLAN_DIR.glob("plan-*.md")})
    else:
        dates = _dates_from_paths(argv)

    missing = [d for d in dates if not _date_in_plan_log(d, log_text)]
    if not missing:
        return 0

    print(
        "plan.md is missing a summary line referencing:\n  - "
        + "\n  - ".join(missing)
        + "\n\nAdd one line per date of the form:\n"
        "  - [Adversarial-Agent @ YYYY-MM-DDTHH:MM:SSZ] one or two lines summary.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
