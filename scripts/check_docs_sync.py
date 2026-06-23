"""Pre-commit + CI hook: enforce that the project's source-of-truth docs exist
and reference each other consistently.

Specifically:
    * `AGENTS.md` must exist at the repo root.
    * `db_structured.md` must exist at the repo root.
    * `plan.md` must exist at the repo root and contain at least one
      signed daily-summary line (looks for an agent identity in parens).
    * `docs/plan/` must contain at least one dated plan file.
    * `docs/artifacts/README.md` must exist.

This catches the most common "I forgot to update the docs" mistake before
it lands.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "db_structured.md",
    ROOT / "plan.md",
    ROOT / "docs" / "artifacts" / "README.md",
]

# matches "(Adversarial-Agent, 2026-06-23 17:42 UTC)" etc.
SIGNATURE_RE = re.compile(r"\(([A-Za-z][A-Za-z0-9-]+-Agent),\s*\d{4}-\d{2}-\d{2}.*UTC\)")

DATED_PLAN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print("error: required project docs are missing:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    plan_text = (ROOT / "plan.md").read_text(encoding="utf-8")
    if not SIGNATURE_RE.search(plan_text):
        print(
            "error: plan.md has no agent-signed entry. expected pattern like "
            "'(Adversarial-Agent, 2026-06-23 17:42 UTC)'.",
            file=sys.stderr,
        )
        return 1

    plan_dir = ROOT / "docs" / "plan"
    dated = [p for p in plan_dir.glob("*.md") if DATED_PLAN_RE.match(p.name)]
    if not dated:
        print(
            "error: docs/plan/ has no dated plan files (YYYY-MM-DD.md).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
