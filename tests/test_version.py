from __future__ import annotations

from specint._version import get_extractor_git, reset_cache_for_tests


def test_extractor_git_uses_override(monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "abcdef123456789")
    reset_cache_for_tests()
    try:
        assert get_extractor_git() == "abcdef123456"
    finally:
        reset_cache_for_tests()


def test_extractor_git_uses_github_sha(monkeypatch):
    monkeypatch.delenv("SPECINT_EXTRACTOR_GIT", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "deadbeefcafe12345678")
    reset_cache_for_tests()
    try:
        assert get_extractor_git() == "deadbeefcafe"
    finally:
        reset_cache_for_tests()


def test_extractor_git_no_env_falls_back(monkeypatch):
    monkeypatch.delenv("SPECINT_EXTRACTOR_GIT", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    reset_cache_for_tests()
    try:
        value = get_extractor_git()
        # Either a git short SHA (>=1 char) or "dev". Never empty.
        assert value
        assert value != "GITHUB_SHA"
    finally:
        reset_cache_for_tests()


def test_provenance_stamps_git_sha(monkeypatch):
    from specint.records import Provenance

    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "fixedcommit1")
    reset_cache_for_tests()
    try:
        prov = Provenance(extractor="test")
        assert prov.extractor_git == "fixedcommit1"
    finally:
        reset_cache_for_tests()
