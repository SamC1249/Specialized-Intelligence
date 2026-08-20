"""Language-detection heuristic tests."""

from __future__ import annotations

import pytest

from specint.quality.lang import detect_from_record, detect_language
from specint.records import Provenance, VideoRecord


@pytest.mark.parametrize(
    "text,expected",
    [
        ("How to make the best pasta recipe with garlic and butter", "en"),
        ("Cómo hacer una receta de paella para una cena con amigos", "es"),
        ("Comment cuisiner une recette de tarte au citron avec les enfants", "fr"),
        ("パスタの作り方 レシピを紹介します", "ja"),
        ("如何做西红柿炒鸡蛋 家常菜谱", "zh"),
        ("Как приготовить борщ пошаговый рецепт", "ru"),
        ("", None),
        ("!!!", None),
        ("qwerty asdf zxcv", None),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detect_from_record_uses_title_and_description():
    prov = Provenance(extractor="test")
    record = VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/1",
        title="Rezept",
        description="Ein einfaches Rezept mit Butter und für die ganze Familie kochen",
        provenance=prov,
    )
    assert detect_from_record(record) == "de"
