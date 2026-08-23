"""Multilingual cooking-vocabulary hit-rate scorer.

The intuition: a video's text metadata (title, description, keywords,
recipe steps) is "cooking-like" to the extent that it uses recognized
cooking verbs / nouns from at least one language. This gives us a
measurable, language-aware alternative to the previous
``text_density``-only heuristic.

We keep the vocabulary small, hand-curated, and reviewable. It is a
config, not a model. Adding a language:
  1. Extend ``VOCAB_BY_LANG`` with a BCP-47 key + tuple of lowercase
     stemless roots.
  2. Update the tests in ``tests/test_quality_vocab.py`` with at least
     one positive and one negative example for that language.

Scoring:
  - Tokenize the concatenation of title, description, keywords, and
    recipe_steps into unicode word-like chunks (regex ``\\w+``).
  - Also perform substring matching for logographic scripts (e.g.
    Chinese, Japanese) where token boundaries do not correspond to
    words.
  - ``hits / (hits + K)`` with K=3 gives us a saturating score in
    ``[0, 1]`` that rewards diversity, not repetition.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

VOCAB_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "cook",
        "cooking",
        "recipe",
        "bake",
        "baking",
        "fry",
        "frying",
        "roast",
        "boil",
        "simmer",
        "sauté",
        "saute",
        "grill",
        "chop",
        "dice",
        "mince",
        "knead",
        "whisk",
        "kitchen",
        "oven",
        "stove",
        "pan",
        "skillet",
        "chef",
        "ingredient",
        "dough",
        "batter",
        "marinate",
        "season",
        "garnish",
        "plate",
    ),
    "es": (
        "cocinar",
        "cocina",
        "receta",
        "hornear",
        "freír",
        "asar",
        "hervir",
        "picar",
        "sofreír",
        "amasar",
        "ingrediente",
        "cocinero",
        "sartén",
    ),
    "fr": (
        "cuisiner",
        "cuisine",
        "recette",
        "cuire",
        "cuisson",
        "frire",
        "rôtir",
        "bouillir",
        "mijoter",
        "hacher",
        "pétrir",
        "fouetter",
        "ingrédient",
        "chef",
        "casserole",
        "poêle",
    ),
    "it": (
        "cucinare",
        "cucina",
        "ricetta",
        "cuocere",
        "friggere",
        "arrostire",
        "bollire",
        "sobbollire",
        "tritare",
        "impastare",
        "ingrediente",
    ),
    "de": (
        "kochen",
        "küche",
        "rezept",
        "backen",
        "braten",
        "kochen",
        "sieden",
        "hacken",
        "kneten",
        "zutat",
        "koch",
        "pfanne",
        "ofen",
    ),
    "pt": (
        "cozinhar",
        "cozinha",
        "receita",
        "assar",
        "fritar",
        "ferver",
        "picar",
        "amassar",
        "ingrediente",
        "cozinheiro",
    ),
    "ja": ("料理", "レシピ", "作り方", "焼く", "煮る", "炒める", "揚げる", "包丁", "台所"),
    "zh": ("烹饪", "食谱", "做菜", "菜谱", "煮", "炒", "煎", "烤", "蒸", "厨房", "厨师"),
    "ko": ("요리", "레시피", "만드는", "굽기", "볶기", "찌기", "튀김", "부엌", "요리사"),
    "hi": ("पकाना", "रेसिपी", "खाना", "बनाना", "तलना", "भूनना", "रसोई"),
    "ar": ("طبخ", "وصفة", "طهي", "قلي", "شوي", "خبز", "مطبخ", "طاهي"),
    "ru": ("готовить", "рецепт", "жарить", "варить", "запекать", "тушить", "кухня", "повар"),
}

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_LOGOGRAPHIC_LANGS: tuple[str, ...] = ("ja", "zh", "ko", "hi", "ar")
_SATURATION_K = 3.0


def _flatten_text(record: VideoRecord) -> str:
    parts = [record.title or "", record.description or ""]
    parts.extend(record.keywords or [])
    parts.extend(record.recipe_steps or [])
    return " \n ".join(parts).lower()


def _count_hits(text: str) -> tuple[int, set[str]]:
    tokens = set(_TOKEN_RE.findall(text))
    matched: set[str] = set()
    for lang, terms in VOCAB_BY_LANG.items():
        for term in terms:
            t = term.lower()
            if lang in _LOGOGRAPHIC_LANGS or not t.isascii():
                if t and t in text:
                    matched.add(t)
            else:
                if t in tokens:
                    matched.add(t)
    return len(matched), matched


def cooking_vocab_score(record: VideoRecord) -> float:
    text = _flatten_text(record)
    if not text.strip():
        return 0.0
    hits, _ = _count_hits(text)
    if hits <= 0:
        return 0.0
    return hits / (hits + _SATURATION_K)


def matched_terms(record: VideoRecord) -> set[str]:
    """Debug helper: return the set of vocabulary terms this record matched."""
    _, matched = _count_hits(_flatten_text(record))
    return matched


def all_terms(langs: Iterable[str] | None = None) -> list[str]:
    keys = list(VOCAB_BY_LANG.keys()) if langs is None else list(langs)
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        for term in VOCAB_BY_LANG.get(k, ()):
            if term not in seen:
                seen.add(term)
                out.append(term)
    return out
