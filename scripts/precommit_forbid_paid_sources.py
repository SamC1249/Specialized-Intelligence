#!/usr/bin/env python3
"""Pre-commit hook: forbid paid-source / circumvention keywords.

We hard-block keywords that imply either paying for a source or
circumventing a TPM. See docs/artifacts/legal-landscape.md.

Inputs:  list of file paths (from pre-commit)
Outputs: exit 0 on success, 1 on first violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Word-boundary patterns. We allow these in docs/ (to talk about the
# policy itself) but not in code or configs.
FORBIDDEN_PATTERNS = [
    re.compile(r"\bproxy[_-]?rotation\b", re.IGNORECASE),
    re.compile(r"\brotate[_-]?ip\b", re.IGNORECASE),
    re.compile(r"\bbypass[_-]?tpm\b", re.IGNORECASE),
    re.compile(r"\bcircumvent[_-]?drm\b", re.IGNORECASE),
]

ALLOWED_PREFIXES = ("docs/",)


def is_allowed(path: Path) -> bool:
    s = path.as_posix()
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
                    for pat in FORBIDDEN_PATTERNS:
                        if pat.search(line):
                            violations.append((fp, lineno, line.rstrip("\n")))
                            break
        except OSError:
            continue
    if violations:
        print(
            "forbid-paid-source-keywords: a forbidden keyword was found.\n"
            "Repository policy disallows paid-acquisition or TPM-bypass code paths.\n",
            file=sys.stderr,
        )
        for fp, lineno, line in violations:
            print(f"  {fp}:{lineno}: {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
