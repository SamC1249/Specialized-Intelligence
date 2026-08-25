"""Resolve the *exact* extractor git SHA at record-emission time.

AGENTS.md rule #2: "Every record must carry ... the exact extractor
commit hash." The Pydantic default of ``"dev"`` on
``Provenance.extractor_git`` silently violates that whenever an adapter
forgets to override it. This module supplies one canonical resolver
that every adapter uses.

Resolution order:

1. ``SPECINT_GIT_SHA`` environment variable (used by container/CI
   builds where ``.git`` may be stripped from the deployed image).
2. ``.git/HEAD`` walked to a packed or loose ref, first 7 chars.
3. Fallback ``"dev"`` — legal only in a non-git checkout, e.g. a
   ``pip install specint`` sandbox. Adapters must **not** silently
   emit records with ``"dev"`` in production; the regression test
   ``tests/test_provenance.py`` guards this.

The resolved value is cached for the process lifetime; ``.git/HEAD``
does not change under our feet within a single crawl.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

DEV_SHA = "dev"
_ENV_VAR = "SPECINT_GIT_SHA"
_SHORT_SHA_LEN = 7


def _repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _read_head_sha(git_dir: Path) -> str | None:
    head = git_dir / "HEAD"
    if not head.is_file():
        return None
    try:
        contents = head.read_text().strip()
    except OSError:
        return None
    if contents.startswith("ref:"):
        ref = contents.split(" ", 1)[1].strip()
        ref_path = git_dir / ref
        if ref_path.is_file():
            try:
                return ref_path.read_text().strip()
            except OSError:
                return None
        packed = git_dir / "packed-refs"
        if packed.is_file():
            try:
                for line in packed.read_text().splitlines():
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split(" ", 1)
                    if len(parts) == 2 and parts[1].strip() == ref:
                        return parts[0].strip()
            except OSError:
                return None
        return None
    return contents or None


@lru_cache(maxsize=1)
def resolve_extractor_git(start: str | os.PathLike[str] | None = None) -> str:
    """Return the short git SHA the current extractor is running from.

    Never raises. Returns :data:`DEV_SHA` only if every strategy fails.
    """
    env_sha = os.environ.get(_ENV_VAR)
    if env_sha:
        return env_sha.strip()[:_SHORT_SHA_LEN] or DEV_SHA

    origin = Path(start) if start is not None else Path(__file__).resolve()
    root = _repo_root(origin if origin.is_dir() else origin.parent)
    if root is None:
        return DEV_SHA

    git_dir_marker = root / ".git"
    git_dir = git_dir_marker
    if git_dir_marker.is_file():
        # Support git worktrees: `.git` is a file containing "gitdir: <path>".
        try:
            payload = git_dir_marker.read_text().strip()
        except OSError:
            return DEV_SHA
        if payload.startswith("gitdir:"):
            git_dir = Path(payload.split(":", 1)[1].strip())
            if not git_dir.is_absolute():
                git_dir = (root / git_dir).resolve()

    sha = _read_head_sha(git_dir)
    if not sha:
        return DEV_SHA
    return sha[:_SHORT_SHA_LEN]


def reset_cache() -> None:
    """Testing hook. Not part of the public API."""
    resolve_extractor_git.cache_clear()
