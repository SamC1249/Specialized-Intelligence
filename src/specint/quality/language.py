"""Lightweight language inference and multilingual cooking seed terms.

We deliberately avoid pulling in a language-detection dependency; the
goal here is to (a) assign a coarse BCP-47 tag to records that arrive
without one and (b) provide a known-good set of cooking seed terms in
non-English languages so the comparison harness isn't English-only.

Classification is script-first:

  - CJK Unified Ideographs → "zh" (we cannot distinguish zh vs ja from
    Han characters alone; records with Hiragana/Katakana are promoted to
    "ja", and records with Hangul are promoted to "ko").
  - Hiragana / Katakana → "ja".
  - Hangul → "ko".
  - Cyrillic → "ru".
  - Arabic → "ar".
  - Devanagari → "hi".
  - Hebrew → "he".
  - Else (Latin-dominant) → look up a tiny stop-word list to pick
    among en / es / fr / de / it / pt; fall back to "en" when ambiguous.

This is intentionally crude and auditable. Downstream code treating the
tag as truth MUST handle the "unknown" case; we return `None` when input
is empty rather than guessing.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+", re.UNICODE)


_LATIN_STOPWORDS: dict[str, str] = {
    "the": "en",
    "and": "en",
    "with": "en",
    "recipe": "en",
    "cooking": "en",
    "y": "es",
    "con": "es",
    "receta": "es",
    "cocina": "es",
    "para": "es",
    "de": "es",
    "et": "fr",
    "avec": "fr",
    "cuisine": "fr",
    "recette": "fr",
    "pour": "fr",
    "und": "de",
    "mit": "de",
    "kochen": "de",
    "rezept": "de",
    "der": "de",
    "die": "de",
    "con_it": "it",
    "ricetta": "it",
    "cucina": "it",
    "pasta": "it",
    "cozinha": "pt",
    "receita": "pt",
    "com": "pt",
}


def _has_range(text: str, lo: int, hi: int) -> bool:
    for ch in text:
        o = ord(ch)
        if lo <= o <= hi:
            return True
    return False


def _script_language(text: str) -> str | None:
    if _has_range(text, 0x3040, 0x309F) or _has_range(text, 0x30A0, 0x30FF):
        return "ja"
    if _has_range(text, 0xAC00, 0xD7AF):
        return "ko"
    if _has_range(text, 0x4E00, 0x9FFF):
        return "zh"
    if _has_range(text, 0x0400, 0x04FF):
        return "ru"
    if _has_range(text, 0x0600, 0x06FF):
        return "ar"
    if _has_range(text, 0x0900, 0x097F):
        return "hi"
    if _has_range(text, 0x0590, 0x05FF):
        return "he"
    return None


def _latin_language(text: str) -> str | None:
    tokens = [t.lower() for t in _TOKEN_RE.findall(unicodedata.normalize("NFC", text))]
    if not tokens:
        return None
    votes: dict[str, int] = {}
    for t in tokens:
        tag = _LATIN_STOPWORDS.get(t)
        if tag:
            votes[tag] = votes.get(tag, 0) + 1
    if not votes:
        return "en"
    return max(votes.items(), key=lambda kv: (kv[1], kv[0] == "en"))[0]


def detect_language(text: str | None) -> str | None:
    """Return a BCP-47 tag inferred from `text`, or None if `text` is empty.

    Pure, deterministic, and safe to run per-record on millions of titles.
    """
    if not text or not text.strip():
        return None
    text = text.strip()
    script = _script_language(text)
    if script:
        return script
    return _latin_language(text)


SEED_TERMS: dict[str, list[str]] = {
    "en": ["cooking", "recipe", "how to cook"],
    "es": ["cocina", "receta", "como cocinar"],
    "fr": ["cuisine", "recette", "comment cuisiner"],
    "de": ["kochen", "rezept", "wie kocht man"],
    "it": ["cucina", "ricetta", "come cucinare"],
    "pt": ["cozinha", "receita", "como cozinhar"],
    "ja": ["料理", "レシピ", "作り方"],
    "zh": ["烹饪", "食谱", "怎么做菜"],
    "ko": ["요리", "레시피", "만드는 법"],
    "ru": ["кулинария", "рецепт", "как готовить"],
    "ar": ["طبخ", "وصفة", "طريقة الطبخ"],
    "hi": ["खाना बनाना", "रेसिपी"],
    "he": ["בישול", "מתכון"],
}


def seed_terms(language: str | None) -> list[str]:
    """Return the cooking seed terms for a BCP-47 tag.

    Falls back to English when the language is unknown so callers always
    get a usable, non-empty list.
    """
    if not language:
        return list(SEED_TERMS["en"])
    tag = language.lower().split("-", 1)[0]
    return list(SEED_TERMS.get(tag, SEED_TERMS["en"]))


def all_seed_languages() -> Iterable[str]:
    return sorted(SEED_TERMS.keys())
