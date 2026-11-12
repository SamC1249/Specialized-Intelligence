"""Unit tests for cooking-relevance scoring."""

from __future__ import annotations

from datetime import datetime

from specint.quality.relevance import cooking_relevance
from specint.records import License, Provenance, VideoRecord


def _make(title: str, description: str = "", keywords: list[str] | None = None) -> VideoRecord:
    return VideoRecord(
        id=f"test:{title}",
        source="test",
        source_native_id="x",
        url="https://example.test/x",
        title=title,
        description=description,
        keywords=keywords or [],
        license=License.CC0,
        provenance=Provenance(extractor="test", fetched_at=datetime.fromtimestamp(0)),
    )


def test_on_topic_recipe_scores_high() -> None:
    r = _make("Easy Garlic Butter Pasta Recipe", "A 15-minute weeknight pasta with garlic butter.")
    assert cooking_relevance(r) >= 0.9


def test_off_topic_landscape_scores_zero() -> None:
    r = _make("Drone landscape of mountains at sunrise")
    assert cooking_relevance(r) == 0.0


def test_negative_keywords_penalise() -> None:
    r = _make("Football match highlights goal", "Concert later")
    assert cooking_relevance(r) == 0.0


def test_spanish_keywords_hit() -> None:
    r = _make("Receta de paella", "Como cocinar paella en el horno con cuchillo")
    assert cooking_relevance(r) >= 0.6


def test_french_keywords_hit() -> None:
    r = _make("Recette de soupe à l'oignon", "cuisine française avec du pain et beurre")
    assert cooking_relevance(r) >= 0.6


def test_bounds() -> None:
    r_empty = _make("", "")
    assert cooking_relevance(r_empty) == 0.0
    r_saturated = _make("Cooking recipe bake fry roast simmer saute kitchen chef pasta bread soup")
    assert cooking_relevance(r_saturated) == 1.0
