"""Resolve the current repository git SHA once per process.

`Provenance.extractor_git` used to be the literal string `"dev"` on every
record, which makes it impossible to reproduce an old extraction from a
report. This module gives us a single, cached lookup:

    >>> from specint.provenance_git import current_git_sha
    >>> current_git_sha()  # -> "80febdb1..." or "dev" if unresolved

The lookup is deliberately best-effort and *offline*: we shell out to
`git rev-parse --short=12 HEAD` in the repo root and fall back to `"dev"`
on any failure (detached HEAD, missing binary, non-repo checkout).
"""

from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path

FALLBACK = "dev"
_ENV_OVERRIDE = "SPECINT_EXTRACTOR_GIT"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@functools.lru_cache(maxsize=1)
def current_git_sha() -> str:
    override = os.environ.get(_ENV_OVERRIDE)
    if override:
        return override.strip() or FALLBACK

    git = shutil.which("git")
    if git is None:
        return FALLBACK

    try:
        proc = subprocess.run(
            [git, "rev-parse", "--short=12", "HEAD"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return FALLBACK
    if proc.returncode != 0:
        return FALLBACK
    sha = proc.stdout.strip()
    return sha or FALLBACK


def reset_cache() -> None:
    """Clear the cached SHA. Only for tests that mutate env/repo state."""
    current_git_sha.cache_clear()
