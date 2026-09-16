"""Multilingual cooking-relevance scorer tests."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.relevance import (
    COOKING_KEYWORDS,
    is_cooking_relevant,
    score_relevance,
)
from specint.records import Provenance, VideoRecord


def _prov() -> Provenance:
    return Provenance(extractor="t", fetched_at=datetime.now(UTC), query="")


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="",
        description="",
        provenance=_prov(),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_relevance_zero_for_empty_metadata():
    result = score_relevance(_rec())
    assert result.score == 0.0
    assert result.hits == 0
    assert result.matched_languages == ()


def test_relevance_zero_for_offtopic_metadata():
    result = score_relevance(
        _rec(title="Bird migration in the Serengeti", description="Wildlife documentary.")
    )
    assert result.score == 0.0


def test_relevance_english_hit():
    result = score_relevance(
        _rec(title="Easy cooking recipe: pancakes", description="Kitchen basics.")
    )
    assert result.score >= 0.75
    assert "en" in result.matched_languages


def test_relevance_spanish_hit():
    result = score_relevance(
        _rec(title="Cocina fácil: receta de paella", description="Guiso tradicional.")
    )
    assert result.score >= 0.75
    assert "es" in result.matched_languages


def test_relevance_japanese_hit():
    result = score_relevance(
        _rec(title="料理チャンネル: ラーメンのレシピ", description="調理と作り方。")
    )
    assert result.score >= 0.75
    assert "ja" in result.matched_languages


def test_relevance_uses_recipe_steps_and_keywords():
    r = _rec(
        title="Weeknight dinner",
        description="",
        keywords=["pasta"],
        recipe_steps=["Boil water", "Cook pasta", "Serve"],
    )
    result = score_relevance(r)
    assert result.hits >= 1
    assert result.score >= 0.5


def test_all_seed_languages_are_covered():
    for lang in ("en", "es", "fr", "ja", "hi", "zh", "ar"):
        assert lang in COOKING_KEYWORDS


def test_is_cooking_relevant_threshold():
    r_bad = _rec(title="A random travel vlog", description="Trains and mountains.")
    r_good = _rec(title="Cooking pasta with garlic butter", description="Kitchen recipe.")
    assert not is_cooking_relevant(r_bad)
    assert is_cooking_relevant(r_good)
