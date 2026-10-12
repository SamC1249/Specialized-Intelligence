"""Unit tests for the deterministic language detector."""

from __future__ import annotations

import pytest

from specint.quality.language import detect_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "In this short demo we cook garlic butter pasta from scratch. First boil the pasta.",
            "en",
        ),
        (
            "En esta receta vamos a cocinar pasta con mantequilla y ajo hasta que este dorada.",
            "es",
        ),
        (
            "Dans cette recette nous allons cuire les pates avec du beurre et de l ail jusqu a doree.",
            "fr",
        ),
        (
            "In diesem Rezept kochen wir Nudeln mit Butter und Knoblauch bis sie golden sind.",
            "de",
        ),
        (
            "In questa ricetta cuocere la pasta con il burro e l aglio fino a doratura.",
            "it",
        ),
        (
            "Nesta receita vamos cozinhar a massa com manteiga e alho ate ficar dourada.",
            "pt",
        ),
    ],
)
def test_detect_latin_cooking_sentences(text: str, expected: str) -> None:
    assert detect_language(text) == expected


def test_short_input_returns_none() -> None:
    assert detect_language("hi") is None
    assert detect_language("") is None


def test_ambiguous_input_returns_none() -> None:
    # Mixing English + Spanish function words at equal density should refuse to pick.
    text = "the la a el and y of de in en"
    assert detect_language(text) is None


def test_non_latin_input_returns_none() -> None:
    assert detect_language("中文 烹饪 教程 视频") is None
