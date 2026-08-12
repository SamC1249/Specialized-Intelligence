"""Tests for the metadata-only language detector."""

from __future__ import annotations

import pytest

from specint.quality.language import detect_language


@pytest.mark.parametrize(
    "text,expected",
    [
        ("How to make garlic butter pasta at home", "en"),
        ("Receta de tortilla española casera con cebolla", "es"),
        ("Recette de pain de campagne au levain", "fr"),
        ("Rezept für ein einfaches Brot mit Sauerteig", "de"),
        ("Ricetta della pasta al pomodoro con basilico", "it"),
        ("Receita de pão de queijo caseiro", "pt"),
        ("Как приготовить борщ рецепт", "ru"),
        ("和風パスタのレシピ", "ja"),
        ("红烧牛肉的做法", "zh"),
    ],
)
def test_detect_language_common_cases(text, expected):
    assert detect_language(text) == expected


def test_detect_language_returns_none_on_empty():
    assert detect_language("") is None
    assert detect_language("   ") is None


def test_detect_language_returns_none_on_ambiguous_short_text():
    assert detect_language("XYZ 42 foo bar baz qux quux corge") is None
