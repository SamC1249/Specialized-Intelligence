"""Curated multilingual cooking seed terms.

The list is intentionally short (top ~10 terms per language) so it
stays defensible: every entry is either a direct translation of
"cooking / recipe / kitchen / how to cook" or a canonical cooking
verb in that language.

Callers:
  - `all_seed_terms(langs=None)` returns the union across `langs`
    (defaults to every supported language).
  - `terms_for(language)` returns the single-language list.

Adding a language:
  1. Append entries below (all strings must be lowercased normalised).
  2. Update `SUPPORTED_LANGUAGES`.
  3. Add a fixture record for that language under
     `tests/fixtures/<source>/` so the language-detector CI path fires.
"""

from __future__ import annotations

from collections.abc import Iterable

_SEED_TERMS: dict[str, tuple[str, ...]] = {
    "en": (
        "cooking",
        "recipe",
        "how to cook",
        "kitchen",
        "chef",
        "bake",
        "roast",
        "sauté",
        "grill",
        "knife skills",
    ),
    "es": (
        "cocinar",
        "receta",
        "cómo cocinar",
        "cocina",
        "chef",
        "hornear",
        "asar",
        "saltear",
        "parrilla",
        "cortar",
    ),
    "fr": (
        "cuisine",
        "recette",
        "comment cuisiner",
        "cuisiner",
        "chef",
        "cuire",
        "rôtir",
        "sauter",
        "griller",
        "découper",
    ),
    "de": (
        "kochen",
        "rezept",
        "wie kocht man",
        "küche",
        "koch",
        "backen",
        "braten",
        "anbraten",
        "grillen",
        "schneiden",
    ),
    "it": (
        "cucinare",
        "ricetta",
        "come cucinare",
        "cucina",
        "chef",
        "cuocere",
        "arrostire",
        "saltare",
        "grigliare",
        "tagliare",
    ),
    "pt": (
        "cozinhar",
        "receita",
        "como cozinhar",
        "cozinha",
        "chef",
        "assar",
        "grelhar",
        "refogar",
        "cortar",
        "fritar",
    ),
    "ja": (
        "料理",
        "レシピ",
        "作り方",
        "調理",
        "キッチン",
        "焼く",
        "炒める",
        "煮る",
        "揚げる",
        "切る",
    ),
    "zh": (
        "烹饪",
        "食谱",
        "做菜",
        "厨房",
        "炒",
        "炖",
        "蒸",
        "炸",
        "烤",
        "切",
    ),
    "hi": (
        "पकाना",
        "रेसिपी",
        "खाना बनाना",
        "रसोई",
        "तलना",
        "भूनना",
        "उबालना",
        "काटना",
        "पकवान",
        "मसाला",
    ),
    "ar": (
        "طبخ",
        "وصفة",
        "كيفية الطبخ",
        "مطبخ",
        "شواء",
        "قلي",
        "خبز",
        "تقطيع",
        "طبق",
        "طهي",
    ),
}

SUPPORTED_LANGUAGES: tuple[str, ...] = tuple(sorted(_SEED_TERMS.keys()))


def terms_for(language: str) -> list[str]:
    return list(_SEED_TERMS.get(language, ()))


def all_seed_terms(langs: Iterable[str] | None = None) -> list[str]:
    langs = list(langs) if langs else list(SUPPORTED_LANGUAGES)
    seen: set[str] = set()
    out: list[str] = []
    for lang in langs:
        for term in _SEED_TERMS.get(lang, ()):
            if term not in seen:
                seen.add(term)
                out.append(term)
    return out
