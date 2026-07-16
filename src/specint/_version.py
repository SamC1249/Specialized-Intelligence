"""Extractor version resolution.

Provenance must record the exact extractor commit hash. This helper
resolves it deterministically in the following order:

1. `SPECINT_EXTRACTOR_GIT` — explicit override (used by tests).
2. `GITHUB_SHA` — set by GitHub Actions runners.
3. `git rev-parse --short=12 HEAD` — local dev; cached after first call.
4. `"dev"` — only when we are demonstrably outside any git repo.

The resolved value is memoised so that a single process produces a
stable provenance stamp across all records it emits.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache


def _short(value: str) -> str:
    return value.strip()[:12] or "dev"


@lru_cache(maxsize=1)
def get_extractor_git() -> str:
    override = os.environ.get("SPECINT_EXTRACTOR_GIT")
    if override:
        return _short(override)

    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return _short(sha)

    git = shutil.which("git")
    if git:
        try:
            out = subprocess.run(
                [git, "rev-parse", "--short=12", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "dev"
        if out.returncode == 0 and out.stdout.strip():
            return _short(out.stdout)
    return "dev"


def reset_cache_for_tests() -> None:
    """Clear the memoised value. Only intended for tests that inject
    a specific SHA via `SPECINT_EXTRACTOR_GIT`.
    """
    get_extractor_git.cache_clear()
