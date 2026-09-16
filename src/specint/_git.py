"""Resolve the extractor git SHA for provenance.

Priority: `SPECINT_GIT_SHA` env → `GITHUB_SHA` env → `git rev-parse
--short HEAD` in the current repo → the literal string `"dev"`. The
result is cached: `resolve_sha()` is safe to call in tight loops.

The AGENTS.md constraint says every record must carry "the exact
extractor commit hash". This module is the single implementation of
that lookup.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def resolve_sha() -> str:
    for key in ("SPECINT_GIT_SHA", "GITHUB_SHA"):
        val = os.environ.get(key)
        if val:
            return val.strip()[:12] or "dev"
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res.returncode == 0:
            sha = res.stdout.strip()
            if sha:
                return sha
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        pass
    return "dev"


def reset_cache() -> None:
    """Testing hook — the lru_cache would otherwise persist across tests."""
    resolve_sha.cache_clear()
