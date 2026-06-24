#!/usr/bin/env python3
"""Pre-commit hook: fail if any non-doc file contains a YouTube URL.

Rationale (see docs/artifacts/legal-landscape.md): byte-level acquisition
from YouTube is out of scope. This hook keeps acquisition code, tests,
and configs free of YouTube URLs so we cannot accidentally introduce a
yt-dlp call. Documentation and README are exempt because they need to
discuss the policy.

Inputs:  list of file paths (from pre-commit)
Outputs: exit 0 on success, 1 on first violation, with a message.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

YOUTUBE_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)",
    re.IGNORECASE,
)

ALLOWED_PREFIXES = ("docs/",)
ALLOWED_FILES = {"README.md", "AGENTS.md", "plan.md", "db_structured.md"}


def is_allowed(path: Path) -> bool:
    s = path.as_posix()
    if s in ALLOWED_FILES:
        return True
    return any(s.startswith(p) for p in ALLOWED_PREFIXES)


def main(argv: list[str]) -> int:
    files = [Path(p) for p in argv[1:]]
    violations: list[tuple[Path, int, str]] = []
    for fp in files:
        if is_allowed(fp) or not fp.exists():
            continue
        try:
            with fp.open("r", encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if YOUTUBE_RE.search(line):
                        violations.append((fp, lineno, line.rstrip("\n")))
        except OSError:
            continue
    if violations:
        print(
            "forbid-youtube-domains: YouTube URL found in non-doc file(s).\n"
            "Repository policy: byte-level YouTube acquisition is out of scope.\n"
            "If you need to discuss this in prose, put it under docs/.\n",
            file=sys.stderr,
        )
        for fp, lineno, line in violations:
            print(f"  {fp}:{lineno}: {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
