#!/usr/bin/env python3
"""Pre-commit hook: forbid YouTube URLs outside ``docs/``.

The project's hard constraint is that we never download bytes from
YouTube (DMCA-§1201 anti-circumvention exposure per
``docs/plan-2026-06-20.md``). To enforce this at the lowest level, we
fail any commit that introduces an ``http(s)://...`` URL whose host is
``youtube.com`` / ``youtu.be`` in a tracked file that is *not* under
``docs/``.

A line containing ``noqa: forbid-youtube`` is exempt (used for the
script's own self-documentation; do not abuse).

The hook is invoked by pre-commit with the staged file paths as
arguments. It also works standalone — without arguments it scans every
file tracked by git that is outside ``docs/``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

YOUTUBE_RE = re.compile(r"https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be)\b")
NOQA_RE = re.compile(r"noqa:\s*forbid-youtube", flags=re.IGNORECASE)

ALLOWED_DIRS = ("docs/", "docs\\")


def _is_text(path: Path) -> bool:
    """Best-effort text detection; binaries are skipped."""
    try:
        path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, OSError):
        return False
    return True


def _tracked_files() -> list[str]:
    try:
        out = subprocess.check_output(["git", "ls-files"], stderr=subprocess.DEVNULL, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in out.splitlines() if line]


def check_files(files: list[str]) -> int:
    failures: list[tuple[str, int, str]] = []
    for relpath in files:
        if relpath.startswith(ALLOWED_DIRS):
            continue
        p = Path(relpath)
        if not p.is_file() or not _is_text(p):
            continue
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if YOUTUBE_RE.search(line) and not NOQA_RE.search(line):
                failures.append((relpath, lineno, line.strip()))
    for relpath, lineno, line in failures:
        print(f"::error file={relpath},line={lineno}::YouTube URL forbidden: {line}")
    if failures:
        print(
            "Forbidden YouTube URLs detected outside docs/. "
            "If this is intentional research context, place it under docs/.",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    files = argv[1:] if len(argv) > 1 else _tracked_files()
    return check_files(files)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
