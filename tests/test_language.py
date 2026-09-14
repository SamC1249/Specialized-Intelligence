"""Language-detector tests. Signal-only — never used for licensing."""

from __future__ import annotations

import pytest

from specint.language import detect_language, is_confidently_tagged


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        (("Add the pasta and stir until the sauce reduces by half. Step 3: minutes.",), "en"),
        (("Recette de cuisine: ajouter la sauce et cuire jusqu'à réduction.",), "fr"),
        (("Rezept: mit soße und einer prise salz für 10 minuten kochen.",), "de"),
        (("Ricetta: aggiungere il sugo con la pasta e cucinare per 10 minuti.",), "it"),
        (("Receta de cocina: añadir la salsa y cocinar por 10 minutos con sal.",), "es"),
        (("料理のレシピ: パスタと ソース を 作り方 で 混ぜます 。",), "ja"),
        (("红烧牛肉的做法与食谱, 烹饪教程",), "zh"),
        (("Рецепт кухни: готовка соуса на 10 минут",), "ru"),  # noqa: RUF001
    ],
)
def test_detects_target_language(texts: tuple[str, ...], expected: str) -> None:
    assert detect_language(*texts) == expected


def test_uncertain_returns_none() -> None:
    assert detect_language("") is None
    assert detect_language("chocolate") is None  # single ambiguous token


def test_is_confidently_tagged_matches_detect() -> None:
    assert is_confidently_tagged("Add the sauce and stir until the pasta is done.") is True
    assert is_confidently_tagged("") is False
