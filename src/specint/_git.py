"""Resolve the extractor commit SHA.

AGENTS.md requires every record to carry "the exact extractor commit hash".
Previously `Provenance.extractor_git` defaulted to `"dev"`, which silently
violated the provenance constraint for every record emitted by CI or local
runs. Resolution order:

1. `SPECINT_GIT_SHA` environment variable (preferred for CI/containers
   where the git tree may not be available at runtime).
2. `git rev-parse --short=12 HEAD` run against the directory that
   contains this file.
3. A build-time baked SHA written to `src/specint/_git_build_sha.txt`
   by packaging / wheel builds.
4. The literal `"dev"` if nothing else is available, with a one-shot
   `warnings.warn` so an operator sees the degradation.

The result is cached because `git rev-parse` is slow enough to show up
in hot paths that construct a `Provenance` per record.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import warnings
from functools import lru_cache
from pathlib import Path

_BAKED_FILE = Path(__file__).with_name("_git_build_sha.txt")
_FALLBACK = "dev"


def _from_env() -> str | None:
    sha = os.environ.get("SPECINT_GIT_SHA", "").strip()
    return sha or None


def _from_git() -> str | None:
    git = shutil.which("git")
    if not git:
        return None
    pkg_dir = Path(__file__).resolve().parent
    try:
        result = subprocess.run(
            [git, "rev-parse", "--short=12", "HEAD"],
            cwd=pkg_dir,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _from_baked() -> str | None:
    try:
        text = _BAKED_FILE.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return text or None


@lru_cache(maxsize=1)
def short_sha() -> str:
    for resolver in (_from_env, _from_git, _from_baked):
        sha = resolver()
        if sha:
            return sha
    warnings.warn(
        "specint: could not resolve extractor_git (no SPECINT_GIT_SHA, no git, no "
        "baked SHA); provenance will record 'dev'",
        RuntimeWarning,
        stacklevel=2,
    )
    return _FALLBACK


def reset_cache() -> None:
    """Testing hook — clears the memoised SHA so env overrides apply."""
    short_sha.cache_clear()
