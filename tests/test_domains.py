"""Tests for the domain registry."""

from __future__ import annotations

import pytest

from specint.domains import (
    COOKING,
    DEFAULT_DOMAIN_SLUG,
    REGISTRY,
    contains_blocklisted,
    domain_slugs,
    get,
    verb_hit_count,
)


def test_default_domain_is_registered():
    assert DEFAULT_DOMAIN_SLUG in REGISTRY
    assert get(DEFAULT_DOMAIN_SLUG).slug == DEFAULT_DOMAIN_SLUG


def test_all_domains_have_disjoint_slugs_and_non_empty_vocab():
    slugs = domain_slugs()
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        d = get(slug)
        assert d.seed_terms, f"{slug} has no seed terms"
        assert d.verb_vocab, f"{slug} has no verb vocab"
        assert d.blocklist_terms, f"{slug} has no blocklist"


def test_unknown_domain_raises():
    with pytest.raises(KeyError):
        get("nonexistent-domain")


def test_verb_hit_count_prefix_matching():
    text = "First we chop the garlic, then we chopped the onions, then we sauté."
    hits = verb_hit_count(text, COOKING.verb_vocab)
    # chop, chopped -> 2 chop hits; sauté -> 1 sauté hit.
    assert hits >= 3


def test_verb_hit_count_word_boundary_prevents_false_positives():
    assert verb_hit_count("Buy chopsticks at the store", COOKING.verb_vocab) == 0


def test_verb_hit_count_zero_on_empty_text():
    assert verb_hit_count("", COOKING.verb_vocab) == 0


def test_blocklist_detection():
    assert contains_blocklisted("Amazing cooking MONTAGE!", COOKING.blocklist_terms)
    assert contains_blocklisted("Behind the scenes trailer", COOKING.blocklist_terms)
    assert not contains_blocklisted("How to chop garlic properly", COOKING.blocklist_terms)


def test_all_domain_verb_vocabs_are_lowercase():
    # The verb_hit_count implementation lowercases input; keeping vocabs
    # lowercase as well makes the invariant obvious to future editors.
    for slug in domain_slugs():
        d = get(slug)
        for verb in d.verb_vocab:
            assert verb == verb.lower(), f"domain {slug} verb {verb!r} is not lowercase"
