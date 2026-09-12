"""Query presets — thin data-only module so scrapers stay language-agnostic.

Rationale: cooking terms vary sharply by language; a scraper hitting
Wikimedia Commons with only English seed terms leaves a huge fraction
of legally-clean footage unreachable. This module centralises the
term lists so every source consumes the same vocabulary.

Adding a preset:
  - Keep each list under ~20 terms; larger lists explode search-API
    result counts without improving recall.
  - Terms must be search-engine friendly (single words or 2-word
    phrases; no quoted expressions here).
  - Add a matching `test_queries.py` case pinning expected size and
    presence of an anchor term.

The `PRESETS` map is the single lookup; the CLI's `--preset` flag
resolves against it.
"""

from __future__ import annotations

COOKING_EN: list[str] = [
    "cooking",
    "recipe",
    "how to cook",
    "kitchen skills",
    "knife skills",
    "baking tutorial",
    "food preparation",
]

COOKING_MULTILINGUAL: list[str] = [
    "cooking",
    "recipe",
    "cocina",
    "receta",
    "cuisine",
    "recette",
    "kochen",
    "rezept",
    "cucina",
    "ricetta",
    "料理",
    "レシピ",
    "요리",
    "레시피",
    "烹饪",
    "食谱",
    "receita",
    "готовить",
]

PROCEDURAL_GENERIC: list[str] = [
    "tutorial",
    "how to",
    "step by step",
    "demonstration",
    "walkthrough",
]

DIFFICULT_VIDEO_DOMAINS: dict[str, list[str]] = {
    "cooking": COOKING_EN,
    "cooking_multi": COOKING_MULTILINGUAL,
    "surgery": ["surgical technique", "operating room", "laparoscopy demonstration"],
    "lab": ["laboratory protocol", "pipetting technique", "chemistry demonstration"],
    "sports": ["training drill", "skill demonstration", "coaching tutorial"],
    "manufacturing": ["assembly line", "machining tutorial", "manufacturing process"],
}

PRESETS: dict[str, list[str]] = {
    "cooking": COOKING_EN,
    "cooking_multi": COOKING_MULTILINGUAL,
    "procedural": PROCEDURAL_GENERIC,
}


def resolve_preset(name: str) -> list[str]:
    try:
        return list(PRESETS[name])
    except KeyError as exc:
        available = ", ".join(sorted(PRESETS))
        raise KeyError(f"unknown preset {name!r}; available: {available}") from exc


__all__ = [
    "COOKING_EN",
    "COOKING_MULTILINGUAL",
    "DIFFICULT_VIDEO_DOMAINS",
    "PRESETS",
    "PROCEDURAL_GENERIC",
    "resolve_preset",
]
