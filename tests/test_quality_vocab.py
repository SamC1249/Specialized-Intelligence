from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.vocab import (
    all_terms,
    cooking_vocab_score,
    matched_terms,
)
from specint.records import Provenance, VideoRecord


def _rec(title: str = "", description: str = "", keywords=None, steps=None) -> VideoRecord:
    return VideoRecord(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title=title,
        description=description,
        keywords=keywords or [],
        recipe_steps=steps or [],
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


def test_empty_record_scores_zero():
    assert cooking_vocab_score(_rec()) == 0.0


def test_english_cooking_record_scores_high():
    r = _rec(
        title="How to bake sourdough bread",
        description="A kitchen tutorial: mix, knead, and bake the dough in the oven.",
        keywords=["baking", "recipe"],
    )
    score = cooking_vocab_score(r)
    assert score > 0.6
    matched = matched_terms(r)
    assert "bake" in matched
    assert "kitchen" in matched


def test_non_cooking_english_scores_zero():
    r = _rec(
        title="Quarterly earnings call transcript",
        description="Discussion of enterprise revenue growth and forward guidance.",
    )
    assert cooking_vocab_score(r) == 0.0


def test_multilingual_positive_examples():
    # Japanese
    ja = _rec(title="簡単な料理のレシピ", description="家庭で作る和食の作り方")
    # French
    fr = _rec(
        title="Recette facile de ratatouille",
        description="Tutoriel cuisine pour cuisiner à la maison.",
    )
    # Chinese
    zh = _rec(title="家常菜谱: 简单做菜教程", description="厨房里的烹饪示范。")
    for r in (ja, fr, zh):
        assert cooking_vocab_score(r) > 0.4, f"expected cooking-y score for {r.title!r}"


def test_all_terms_dedupes():
    terms = all_terms()
    assert len(terms) == len(set(terms))
    assert "recipe" in terms
