"""Read the current git short SHA without shelling out to `git`.

We prefer a subprocess-free approach so import remains fast, tests are
deterministic (no PATH shenanigans in CI), and detached-source tarballs
gracefully degrade to `"unknown"`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def short_sha(root: Path | None = None) -> str:
    """Return the 7-char short SHA of HEAD, or ``"unknown"`` on failure.

    Walks up parent directories starting at `root` (or this file's location)
    looking for a `.git` directory; supports the git-worktree case where
    `.git` is a text file pointing at `gitdir: /abs/path/to/gitdir`.
    """
    start = root or Path(__file__).resolve()
    if start.is_file():
        start = start.parent
    for candidate in [start, *start.parents]:
        git = candidate / ".git"
        if git.exists():
            gitdir = _resolve_gitdir(git)
            if gitdir is None:
                continue
            sha = _read_head(gitdir)
            if sha:
                return sha[:7]
            return "unknown"
    return "unknown"


def _resolve_gitdir(git_path: Path) -> Path | None:
    if git_path.is_dir():
        return git_path
    try:
        contents = git_path.read_text().strip()
    except OSError:
        return None
    if contents.startswith("gitdir:"):
        pointed = Path(contents.split(":", 1)[1].strip())
        if not pointed.is_absolute():
            pointed = git_path.parent / pointed
        return pointed if pointed.exists() else None
    return None


def _read_head(gitdir: Path) -> str | None:
    head = gitdir / "HEAD"
    if not head.exists():
        return None
    try:
        content = head.read_text().strip()
    except OSError:
        return None
    if content.startswith("ref:"):
        ref = content.split(":", 1)[1].strip()
        ref_path = gitdir / ref
        if ref_path.exists():
            try:
                return ref_path.read_text().strip()
            except OSError:
                return None
        packed = gitdir / "packed-refs"
        if packed.exists():
            try:
                for line in packed.read_text().splitlines():
                    if line.startswith("#") or line.startswith("^"):
                        continue
                    sha, _, name = line.partition(" ")
                    if name.strip() == ref:
                        return sha
            except OSError:
                return None
        return None
    return content or None
