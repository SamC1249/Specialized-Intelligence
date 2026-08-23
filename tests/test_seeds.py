from __future__ import annotations

from specint.seeds import SEEDS_BY_LANG, known_languages, seeds_for


def test_seeds_covers_target_languages():
    for lang in ("en", "es", "fr", "it", "de", "pt", "ja", "zh", "ko", "hi", "ar", "ru"):
        assert lang in SEEDS_BY_LANG, f"missing seed language: {lang}"
        assert SEEDS_BY_LANG[lang], f"empty seed list: {lang}"


def test_seeds_for_returns_all_by_default():
    all_terms = seeds_for()
    assert "cooking" in all_terms
    assert "料理" in all_terms
    assert len(all_terms) == len(set(all_terms))


def test_seeds_for_filters_by_lang():
    fr = seeds_for(["fr"])
    assert "recette" in fr
    assert "cooking" not in fr


def test_seeds_for_unknown_lang_is_silent():
    assert seeds_for(["klingon"]) == []


def test_known_languages_matches_dict():
    assert set(known_languages()) == set(SEEDS_BY_LANG.keys())
