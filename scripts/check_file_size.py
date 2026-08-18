#!/usr/bin/env python3
"""Fail if any tracked source/doc file exceeds 800 lines.

AGENTS.md: "keep individual files under ~800 lines". Enforced in CI so
the rule bites at review time, not on the reviewer.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAX_LINES = 800
IGNORED_SUFFIXES = {
    ".json",
    ".ndjson",
    ".jsonl",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ico",
    ".mp4",
    ".webm",
    ".ogv",
    ".zip",
    ".gz",
    ".tar",
    ".pdf",
    ".ipynb",
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(p) for p in out.splitlines() if p]


def main() -> int:
    offenders: list[tuple[str, int]] = []
    for path in tracked_files():
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        if lines > MAX_LINES:
            offenders.append((str(path), lines))

    if offenders:
        print(f"::error::Files exceeding {MAX_LINES}-line cap:", file=sys.stderr)
        for name, n in offenders:
            print(f"  {name}: {n} lines", file=sys.stderr)
        return 1
    print(f"OK: no tracked file exceeds {MAX_LINES} lines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
