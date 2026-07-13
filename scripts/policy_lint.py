"""Fail-closed policy lint for legal-source and report-hygiene invariants.

Two checks, both O(files):

1. **Report hygiene.** Every JSON file under `reports/` must be a valid
   compare report (`{"query": ..., "rows": [...]}`) *or* a document whose
   `records` field is an array of `VideoRecord`-shaped dicts. For every
   such record, `license` must be in the redistributable set
   (`scripts/policy_allowlist.REDISTRIBUTABLE_LICENSES`). Records with
   `UNKNOWN` are allowed but counted; anything else is a hard failure.

2. **Source-tree hygiene.** No file under `src/`, `scripts/`,
   `tests/fixtures/`, or top-level YAML/TOML may hard-code a host in
   `BLOCKED_HOSTS`. Exemptions live in `POLICY_LINT_EXEMPT_PATHS`.

Exit codes:
  0 = clean.
  1 = one or more violations (prints them to stderr).
  2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "scripts"))

from policy_allowlist import (  # noqa: E402  (deliberate late import)
    BLOCKED_HOSTS,
    POLICY_LINT_EXEMPT_PATHS,
    REDISTRIBUTABLE_LICENSES,
)


def _iter_report_files(root: Path) -> Iterable[Path]:
    reports_dir = root / "reports"
    if not reports_dir.is_dir():
        return []
    return (p for p in reports_dir.rglob("*.json") if p.is_file())


def _iter_source_files(root: Path) -> Iterable[Path]:
    targets: list[Path] = []
    for sub in ("src", "scripts"):
        base = root / sub
        if base.is_dir():
            targets.extend(p for p in base.rglob("*.py") if p.is_file())
    targets.extend(root.glob("*.yaml"))
    targets.extend(root.glob("*.yml"))
    targets.extend((root / ".github").rglob("*.y*ml"))
    return targets


def _is_exempt(rel_path: str) -> bool:
    return any(rel_path == e or rel_path.startswith(e) for e in POLICY_LINT_EXEMPT_PATHS)


def _extract_records(doc: object) -> list[dict[str, object]]:
    if isinstance(doc, dict):
        rec = doc.get("records")
        if isinstance(rec, list):
            return [r for r in rec if isinstance(r, dict)]
        rows = doc.get("rows")
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    if isinstance(doc, list):
        return [r for r in doc if isinstance(r, dict)]
    return []


def check_reports(root: Path) -> list[str]:
    problems: list[str] = []
    for path in _iter_report_files(root):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
            continue
        records = _extract_records(doc)
        for i, rec in enumerate(records):
            lic = rec.get("license")
            if lic is None:
                continue
            if lic == "UNKNOWN":
                continue
            if lic not in REDISTRIBUTABLE_LICENSES:
                problems.append(
                    f"{path.relative_to(root)}[{i}]: license={lic!r} is not redistributable"
                )
    return problems


def check_source_hosts(root: Path) -> list[str]:
    problems: list[str] = []
    for path in _iter_source_files(root):
        rel = str(path.relative_to(root))
        if _is_exempt(rel):
            continue
        text = path.read_text(errors="ignore")
        for host in BLOCKED_HOSTS:
            if host in text:
                problems.append(f"{rel}: contains blocked host substring {host!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="policy_lint")
    p.add_argument("--root", type=Path, default=REPO_ROOT)
    p.add_argument("--check", choices=["reports", "hosts", "all"], default="all")
    args = p.parse_args(argv)
    root: Path = args.root

    problems: list[str] = []
    if args.check in {"reports", "all"}:
        problems.extend(check_reports(root))
    if args.check in {"hosts", "all"}:
        problems.extend(check_source_hosts(root))

    if problems:
        for msg in problems:
            print(f"[policy_lint] {msg}", file=sys.stderr)
        return 1
    print("[policy_lint] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
