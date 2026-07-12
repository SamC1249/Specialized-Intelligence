from __future__ import annotations

import pytest

from specint.domains import (
    COOKING,
    DEFAULT_DOMAIN,
    LABORATORY,
    MANUFACTURING,
    SPORTS,
    SURGERY,
    Domain,
    get_domain,
    list_domains,
)


def test_default_domain_is_cooking():
    assert DEFAULT_DOMAIN is COOKING
    assert DEFAULT_DOMAIN.slug == "cooking"


def test_all_known_domains_are_registered():
    slugs = {d.slug for d in list_domains()}
    assert slugs == {"cooking", "laboratory", "surgery", "sports", "manufacturing"}


def test_get_domain_by_slug():
    assert get_domain("cooking") is COOKING
    assert get_domain("laboratory") is LABORATORY
    assert get_domain("surgery") is SURGERY
    assert get_domain("sports") is SPORTS
    assert get_domain("manufacturing") is MANUFACTURING


def test_unknown_slug_raises_with_hint():
    with pytest.raises(KeyError) as info:
        get_domain("cinema")
    assert "cinema" in str(info.value)
    assert "cooking" in str(info.value)


def test_domain_is_frozen():
    with pytest.raises(ValueError):
        COOKING.seed_terms = ()  # type: ignore[misc]


def test_procedural_verbs_are_non_empty_and_lowercase():
    for d in list_domains():
        assert d.procedural_verbs, f"{d.slug} has no verbs"
        for verb in d.procedural_verbs:
            assert verb.islower(), f"{d.slug}: verb {verb!r} must be lowercase"
            assert " " not in verb, f"{d.slug}: verb {verb!r} must be a single token"


def test_domain_slug_validation():
    Domain(
        slug="valid_slug",
        display_name="ok",
        seed_terms=("a",),
        procedural_verbs=("run",),
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Domain(
            slug="Invalid-Slug",
            display_name="nope",
            seed_terms=("a",),
            procedural_verbs=("run",),
        )
