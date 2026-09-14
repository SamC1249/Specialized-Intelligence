"""Contract tests for the domain registry."""

from __future__ import annotations

import pytest

from specint.domains import DOMAINS, list_domains, list_languages, terms_for


def test_registry_has_expected_domains() -> None:
    assert set(list_domains()) >= {"cooking", "surgery", "manufacturing"}


def test_every_domain_has_english_seed() -> None:
    for domain in list_domains():
        assert "en" in DOMAINS[domain], f"{domain} missing English seed terms"
        assert len(DOMAINS[domain]["en"]) >= 3


def test_terms_for_specific_language() -> None:
    assert terms_for("cooking", "en") == list(DOMAINS["cooking"]["en"])
    assert "料理" in terms_for("cooking", "ja")


def test_terms_for_union_dedups() -> None:
    union = terms_for("cooking")
    assert len(union) == len(set(union))
    for term in DOMAINS["cooking"]["en"]:
        assert term in union


def test_unknown_domain_raises() -> None:
    with pytest.raises(KeyError):
        terms_for("does-not-exist")


def test_unknown_language_raises() -> None:
    with pytest.raises(KeyError):
        terms_for("cooking", "xx")


def test_list_languages_sorted() -> None:
    langs = list_languages("cooking")
    assert langs == sorted(langs)
