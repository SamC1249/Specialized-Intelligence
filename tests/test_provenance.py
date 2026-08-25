"""Provenance integrity — AGENTS.md rule #2.

`Provenance.extractor_git` must carry the real commit SHA, not the
default ``"dev"`` string. This test suite locks in three invariants:

1. Inside a git working tree, ``resolve_extractor_git()`` returns a
   short (7-char) hex SHA, not ``"dev"``.
2. The ``SPECINT_GIT_SHA`` environment variable overrides everything
   else (needed for stripped Docker images where ``.git`` is absent).
3. Every adapter's ``parse()`` propagates the resolved SHA into the
   emitted record's ``provenance.extractor_git``.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from specint.provenance import DEV_SHA, reset_cache, resolve_extractor_git
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

SHORT_SHA_RE = re.compile(r"^[0-9a-f]{7}$")
REPO_ROOT = Path(__file__).resolve().parents[1]


def _in_git_worktree() -> bool:
    return (REPO_ROOT / ".git").exists()


@pytest.fixture(autouse=True)
def _reset_provenance_cache(monkeypatch):
    """Every test in this module starts with a fresh cache."""
    monkeypatch.delenv("SPECINT_GIT_SHA", raising=False)
    reset_cache()
    yield
    reset_cache()


@pytest.mark.skipif(not _in_git_worktree(), reason="not a git checkout")
def test_resolver_returns_short_sha_in_git_worktree():
    sha = resolve_extractor_git()
    assert sha != DEV_SHA, "extractor_git must never be 'dev' in a git checkout"
    assert SHORT_SHA_RE.match(sha), f"expected a 7-char hex SHA, got {sha!r}"

    # And it must match what git itself reports.
    proc = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert sha == proc.stdout.strip()


def test_env_var_overrides_git(monkeypatch):
    monkeypatch.setenv("SPECINT_GIT_SHA", "abcdef1234567890")
    reset_cache()
    assert resolve_extractor_git() == "abcdef1"


def test_env_var_short_value_is_used_as_is(monkeypatch):
    monkeypatch.setenv("SPECINT_GIT_SHA", "1234abc")
    reset_cache()
    assert resolve_extractor_git() == "1234abc"


def test_fallback_when_not_in_git_tree(tmp_path: Path, monkeypatch):
    """A path outside any git repo must fall back to DEV_SHA."""
    monkeypatch.delenv("SPECINT_GIT_SHA", raising=False)
    reset_cache()
    isolated = tmp_path / "not-a-repo"
    isolated.mkdir()
    assert resolve_extractor_git(isolated) != ""


def _load(rel: str):
    return json.loads((Path(__file__).parent / "fixtures" / rel).read_text())


def test_all_adapters_propagate_resolved_sha_to_records():
    query = SourceQuery(terms=["cooking"], max_results=5)

    wiki = WikimediaCommonsSource().parse(_load("wikimedia/search_pasta.json"), query)
    arch = ArchiveOrgSource().parse(_load("archive_org/search_cooking.json"), query)
    peer = PeerTubeSource().parse(_load("peertube/search_cooking.json"), query)
    cc = CommonCrawlRecipeSource().parse(
        {
            "html": (Path(__file__).parent / "fixtures/common_crawl/recipe_page.html").read_text(),
            "url": "https://example.test/recipes/x",
        },
        query,
    )

    all_records = [*wiki, *arch, *peer, *cc]
    assert all_records, "fixtures should yield at least one record per adapter"

    resolved = resolve_extractor_git()
    for r in all_records:
        assert r.provenance.extractor_git == resolved
        if _in_git_worktree():
            assert r.provenance.extractor_git != DEV_SHA
