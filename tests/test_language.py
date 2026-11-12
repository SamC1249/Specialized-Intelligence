"""Unit tests for the metadata-only language detector."""

from __future__ import annotations

import pytest

from specint.quality.language import detect_language


@pytest.mark.parametrize(
    "text,expected",
    [
        ("the cat is on the mat and it is sleeping", "en"),
        ("la receta de la paella que cocina en el horno", "es"),
        ("la recette de la soupe à l'oignon avec du pain", "fr"),
        ("das rezept für die suppe mit dem brot und der butter", "de"),
        ("la ricetta della pasta con il burro e la salsa", "it"),
        ("a receita de bolo com manteiga e açúcar no forno", "pt"),
        ("寿司の作り方", "ja"),
        ("中文烹饪视频", "zh"),
        ("पाक कला वीडियो", "hi"),
    ],
)
def test_detect_known_language(text: str, expected: str) -> None:
    assert detect_language(text) == expected


def test_detect_returns_none_on_short_or_ambiguous() -> None:
    assert detect_language("") is None
    assert detect_language("ab") is None
    assert detect_language("xyz 123") is None


def test_detect_is_pure() -> None:
    text = "the recipe calls for garlic and butter"
    assert detect_language(text) == detect_language(text)
