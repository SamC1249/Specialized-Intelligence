"""Provenance-integrity tests."""

from __future__ import annotations

import re
import subprocess

import pytest

from specint.records import Provenance, extractor_git_sha


def test_extractor_git_sha_is_short_hex_or_dev():
    sha = extractor_git_sha()
    assert sha == "dev" or re.fullmatch(r"[0-9a-f]{7,12}", sha), sha


def test_extractor_git_sha_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "deadbeef")
    extractor_git_sha.cache_clear()
    try:
        assert extractor_git_sha() == "deadbeef"
    finally:
        extractor_git_sha.cache_clear()


def test_extractor_git_sha_env_truncates_over_12_chars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPECINT_EXTRACTOR_GIT", "0123456789abcdef0123")
    extractor_git_sha.cache_clear()
    try:
        assert extractor_git_sha() == "0123456789ab"
    finally:
        extractor_git_sha.cache_clear()


def test_provenance_records_extractor_git():
    prov = Provenance(extractor="tests.test_provenance")
    assert prov.extractor_git == extractor_git_sha()
    assert prov.extractor == "tests.test_provenance"


def test_provenance_git_sha_matches_actual_repo_when_present():
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, timeout=2.0
            )
            .decode()
            .strip()
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("git not available")
    if not out:
        pytest.skip("not in a git repo")
    extractor_git_sha.cache_clear()
    assert extractor_git_sha() == out
