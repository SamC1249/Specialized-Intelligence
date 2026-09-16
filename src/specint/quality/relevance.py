"""Metadata-only cooking-relevance scoring.

Motivation (adversarial plan 2026-09-16, H3):
  Metadata quality is domain-agnostic — a 1080p, CC-BY, 5-minute video
  of *bird migration* scores identically to a 5-minute video of
  *chicken curry*. Before we spend GPU minutes decoding frames we
  should push the domain filter as far upstream as possible.

Design constraints:
  * Pure metadata: title + description + keywords + recipe_steps only.
    Never touches the media payload.
  * Multilingual by default, because English-only search terms leave
    the majority of Wikimedia Commons and PeerTube cooking content
    unreachable. Seed languages: English, Spanish, French, Japanese,
    Hindi, Chinese, Arabic.
  * Deterministic and offline-testable. No `langdetect`, no ML.
  * Score is in `[0, 1]` so it can be dropped into `WEIGHTS` with a
    named profile (`quality.profiles`).

Score is a saturating count of matched keyword hits: a single hit
gives 0.5, three or more hits saturate to 1.0. This is intentionally
conservative — the relevance signal is meant to *break ties* between
otherwise equally-clean records, not to be a hard filter on its own.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

# Language → set of lowercase keyword substrings. Kept small and hand-curated
# so behaviour is auditable. Additions must come with a test case.
COOKING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "cook",
        "cooking",
        "recipe",
        "bake",
        "baking",
        "fry",
        "grill",
        "kitchen",
        "chef",
        "cuisine",
        "roast",
        "boil",
        "simmer",
        "sauté",
        "saute",
        "dough",
        "knead",
        "chop",
        "dice",
        "mince",
    ),
    "es": (
        "cocina",
        "cocinar",
        "receta",
        "hornear",
        "freír",
        "freir",
        "sartén",
        "sarten",
        "guiso",
        "salsa",
    ),
    "fr": (
        "cuisine",
        "cuisiner",
        "recette",
        "cuisson",
        "cuit",
        "cuire",
        "poêle",
        "poele",
        "chef",
        "gastronomie",
    ),
    "ja": (
        "料理",
        "レシピ",
        "作り方",
        "焼く",
        "煮る",
        "炒める",
        "調理",
        "厨房",
    ),
    "hi": (
        "पकाना",
        "रेसिपी",
        "खाना",
        "व्यंजन",
        "तलना",
        "भूनना",
    ),
    "zh": (
        "烹饪",
        "食谱",
        "做饭",
        "炒",
        "煮",
        "烤",
        "厨房",
        "菜谱",
    ),
    "ar": (
        "طبخ",
        "وصفة",
        "طهي",
        "مطبخ",
        "قلي",
        "شواء",
    ),
}


@dataclass(frozen=True)
class RelevanceResult:
    score: float
    matched_languages: tuple[str, ...]
    hits: int


def _iter_text(record: VideoRecord) -> Iterable[str]:
    yield record.title or ""
    yield record.description or ""
    yield from record.keywords or ()
    yield from record.recipe_steps or ()


def score_relevance(record: VideoRecord) -> RelevanceResult:
    haystack = " \n ".join(_iter_text(record)).lower()
    if not haystack.strip():
        return RelevanceResult(score=0.0, matched_languages=(), hits=0)

    hits = 0
    matched_langs: list[str] = []
    for lang, keywords in COOKING_KEYWORDS.items():
        lang_hits = 0
        for kw in keywords:
            kw_lc = kw.lower()
            if kw_lc and kw_lc in haystack:
                lang_hits += 1
                hits += 1
        if lang_hits:
            matched_langs.append(lang)

    if hits <= 0:
        score = 0.0
    elif hits == 1:
        score = 0.5
    elif hits == 2:
        score = 0.75
    else:
        score = 1.0

    return RelevanceResult(
        score=score,
        matched_languages=tuple(sorted(matched_langs)),
        hits=hits,
    )


def is_cooking_relevant(record: VideoRecord, threshold: float = 0.5) -> bool:
    return score_relevance(record).score >= threshold
