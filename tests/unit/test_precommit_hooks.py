"""Tests for the custom pre-commit hooks under scripts/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK_YT = REPO / "scripts" / "precommit_forbid_youtube.py"
HOOK_PAID = REPO / "scripts" / "precommit_forbid_paid_sources.py"


def _run(hook: Path, files: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hook), *[str(f) for f in files]],
        capture_output=True,
        text=True,
        check=False,
    )


def test_youtube_hook_passes_on_clean_file(tmp_path: Path):
    f = tmp_path / "clean.py"
    f.write_text("print('hello')\n")
    r = _run(HOOK_YT, [f])
    assert r.returncode == 0, r.stderr


def test_youtube_hook_fails_on_youtube_url(tmp_path: Path):
    f = tmp_path / "bad.py"
    f.write_text("URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'\n")
    r = _run(HOOK_YT, [f])
    assert r.returncode == 1
    assert "youtube" in r.stderr.lower()


def test_youtube_hook_allows_youtube_in_docs(tmp_path: Path):
    """Files under docs/ are allowed to mention YouTube (policy text)."""
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "policy.md"
    f.write_text("We do not download from https://youtube.com/.\n")
    # Run from tmp_path so the hook sees a `docs/` prefix path.
    r = subprocess.run(
        [sys.executable, str(HOOK_YT), "docs/policy.md"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_paid_hook_fails_on_proxy_rotation(tmp_path: Path):
    f = tmp_path / "bad.py"
    f.write_text("def proxy_rotation(): pass\n")
    r = _run(HOOK_PAID, [f])
    assert r.returncode == 1


def test_paid_hook_passes_on_clean(tmp_path: Path):
    f = tmp_path / "clean.py"
    f.write_text("def hello(): return 1\n")
    r = _run(HOOK_PAID, [f])
    assert r.returncode == 0
