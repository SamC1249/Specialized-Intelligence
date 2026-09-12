from __future__ import annotations

import pytest
from specint.queries import (
    COOKING_EN,
    COOKING_MULTILINGUAL,
    DIFFICULT_VIDEO_DOMAINS,
    PRESETS,
    resolve_preset,
)


def test_presets_contain_cooking_and_multilingual():
    assert "cooking" in PRESETS
    assert "cooking_multi" in PRESETS
    assert "procedural" in PRESETS


def test_cooking_en_has_recipe_anchor():
    assert "recipe" in COOKING_EN
    assert "cooking" in COOKING_EN


def test_multilingual_has_multiple_scripts():
    assert any("料理" in t for t in COOKING_MULTILINGUAL)  # ja
    assert any(t == "receta" for t in COOKING_MULTILINGUAL)  # es
    assert any(t == "recette" for t in COOKING_MULTILINGUAL)  # fr


def test_resolve_preset_returns_a_copy():
    a = resolve_preset("cooking")
    a.append("mutation")
    b = resolve_preset("cooking")
    assert "mutation" not in b


def test_resolve_preset_unknown_raises():
    with pytest.raises(KeyError):
        resolve_preset("does-not-exist")


def test_difficult_video_domains_covers_cooking():
    assert "cooking" in DIFFICULT_VIDEO_DOMAINS
    assert DIFFICULT_VIDEO_DOMAINS["cooking"] == COOKING_EN
