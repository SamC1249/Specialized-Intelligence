#!/usr/bin/env python3
"""Fail if any tracked file contains an unresolved `SPECINT-ADVERSARIAL:` marker.

Motivation: Adversarial-Agent leaves markers in code/plans to force
Coding-Agent's attention on specific weak spots. Those markers must not
survive into `main` — either fix the issue or open a follow-up plan
entry, then delete the marker.

Usage:
    python scripts/check_adversarial_todos.py [FILE ...]

If invoked with no arguments, scans every tracked file under version
control (falls back to a filesystem walk if git isn't available).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MARKER = "SPECINT-ADVERSARIAL:"
# Only scan text-ish files; skip binaries and vendor'd directories.
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".txt", ".json"}


def _tracked_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=Path(__file__).resolve().parent.parent
        )
    except (OSError, subprocess.CalledProcessError):
        root = Path(__file__).resolve().parent.parent
        return [p for p in root.rglob("*") if p.is_file() and _is_text_ish(p)]
    paths: list[Path] = []
    root = Path(__file__).resolve().parent.parent
    for chunk in out.split(b"\x00"):
        if not chunk:
            continue
        p = root / chunk.decode("utf-8", errors="replace")
        if p.is_file() and _is_text_ish(p):
            paths.append(p)
    return paths


def _is_text_ish(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES


def _scan(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    try:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if MARKER in line and "check_adversarial_todos" not in line:
                hits.append((i, line.strip()))
    except (OSError, UnicodeDecodeError):
        return []
    return hits


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] if len(argv) > 1 else _tracked_files()
    failures = 0
    for path in paths:
        for lineno, line in _scan(path):
            print(f"{path}:{lineno}: {line}")
            failures += 1
    if failures:
        print(
            f"\nFound {failures} unresolved {MARKER!r} marker(s). Resolve or "
            "reroute to docs/plan-YYYY-MM-DD.md before merging.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
