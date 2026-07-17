"""Unit tests for the multilingual cooking lexicon."""

from __future__ import annotations

from specint.quality.lexicon import DEFAULT_LEXICON, Lexicon


def test_default_lexicon_covers_seed_languages():
    langs = {pack.lang for pack in DEFAULT_LEXICON.packs}
    assert {"en", "es", "fr", "it", "ja", "hi"}.issubset(langs)


def test_match_language_english():
    assert DEFAULT_LEXICON.match_language("Chop garlic and simmer the sauce") == "en"


def test_match_language_spanish():
    assert DEFAULT_LEXICON.match_language("Sofrie el ajo y añade la cebolla, receta rápida") == "es"


def test_match_language_returns_none_on_empty():
    assert DEFAULT_LEXICON.match_language("") is None
    assert DEFAULT_LEXICON.match_language("random unrelated string 12345") is None


def test_verb_and_noun_hit_counts():
    text = "Chop the onion, saute the garlic, then simmer the sauce."
    assert DEFAULT_LEXICON.verb_hits(text) >= 3
    assert DEFAULT_LEXICON.noun_hits(text) >= 2


def test_add_language_extends_matcher():
    lex = Lexicon(packs=list(DEFAULT_LEXICON.packs))
    lex.add_language("de", nouns={"rezept", "kuche"}, verbs={"kochen", "braten"})
    assert lex.match_language("Rezept fur Braten") == "de"


def test_japanese_lexicon_matches_kanji():
    assert DEFAULT_LEXICON.match_language("簡単な料理レシピ: 炒める") == "ja"
