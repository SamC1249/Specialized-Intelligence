"""Provenance must pick up a real git SHA when the environment provides it.

AGENTS.md constraint 2: "Provenance is mandatory. Every record must
carry source URL, license, capture timestamp, and the exact extractor
commit hash." The seed implementation defaulted `extractor_git` to
the literal string `"dev"`, which silently violates the contract in CI.
"""

from __future__ import annotations

import importlib

from specint.records import Provenance


def test_provenance_reads_git_sha_from_env(monkeypatch):
    monkeypatch.setenv("SPECINT_GIT_SHA", "deadbeef1234abcd")
    from specint import records as records_mod

    importlib.reload(records_mod)
    prov = records_mod.Provenance(extractor="t")
    assert prov.extractor_git == "deadbeef1234"


def test_provenance_falls_back_when_env_unset(monkeypatch):
    monkeypatch.delenv("SPECINT_GIT_SHA", raising=False)
    from specint import records as records_mod

    importlib.reload(records_mod)
    prov = records_mod.Provenance(extractor="t")
    assert prov.extractor_git != ""
    assert isinstance(prov.extractor_git, str)


def test_explicit_extractor_git_wins(monkeypatch):
    monkeypatch.setenv("SPECINT_GIT_SHA", "should_not_be_used")
    from specint import records as records_mod

    importlib.reload(records_mod)
    prov = records_mod.Provenance(extractor="t", extractor_git="explicit_sha")
    assert prov.extractor_git == "explicit_sha"


def test_provenance_shape_matches_db_structured_md():
    prov = Provenance(extractor="specint.sources.wikimedia", query="terms=cooking")
    dumped = prov.model_dump(mode="json")
    assert set(dumped) == {"extractor", "extractor_git", "fetched_at", "query"}
