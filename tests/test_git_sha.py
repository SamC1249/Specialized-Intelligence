"""Tests for `specint._git.short_sha` and its wiring into Provenance."""

from __future__ import annotations

import re

import pytest
from specint import _git
from specint.records import Provenance

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


@pytest.fixture(autouse=True)
def _reset_cache():
    _git.reset_cache()
    yield
    _git.reset_cache()


def test_env_override_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPECINT_GIT_SHA", "deadbeefcafe")
    assert _git.short_sha() == "deadbeefcafe"


def test_resolves_to_real_sha_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECINT_GIT_SHA", raising=False)
    sha = _git.short_sha()
    assert sha == "dev" or SHA_RE.match(sha), f"unexpected sha: {sha!r}"


def test_provenance_default_matches_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPECINT_GIT_SHA", "0123456789ab")
    prov = Provenance(extractor="test")
    assert prov.extractor_git == "0123456789ab"


def test_fallback_warns_when_no_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECINT_GIT_SHA", raising=False)
    monkeypatch.setattr(_git, "_from_git", lambda: None)
    monkeypatch.setattr(_git, "_from_baked", lambda: None)
    _git.reset_cache()
    with pytest.warns(RuntimeWarning):
        assert _git.short_sha() == "dev"
