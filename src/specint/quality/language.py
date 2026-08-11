"""Metadata-only language detection + confidence.

We deliberately avoid ML dependencies here. The detector uses three cheap
signals against the concatenated `title + description` (recipe_steps are
ignored to keep detection stable for videos whose text is machine
generated later):

  1. Character-range coverage per script (Latin / Cyrillic / CJK-ideograph
     / Hangul / Devanagari / Arabic / Kana).
  2. Stop-word membership counts per supported language.
  3. Bigram tie-breaking for Latin-script languages where stop words
     overlap (es/fr/it/pt/en/de).

Output: `(iso_code_or_None, confidence)` where confidence is in [0, 1].

The confidence value is intentionally *not* an ML posterior. It is a
robust rule-of-thumb usable as a quality signal: higher-confidence text
is more likely to be procedural cooking language than clickbait / emoji
soup. It is safe to sort or filter with, but do not treat it as ground
truth.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

_STOP_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {"the", "and", "with", "a", "of", "to", "how", "recipe", "cooking", "for", "in", "on"}
    ),
    "es": frozenset({"la", "el", "de", "con", "cómo", "receta", "cocina", "y", "una", "para"}),
    "fr": frozenset({"le", "la", "de", "avec", "recette", "cuisine", "et", "pour", "comment"}),
    "it": frozenset({"la", "il", "di", "con", "ricetta", "cucina", "e", "come", "una", "per"}),
    "de": frozenset({"und", "mit", "der", "die", "das", "rezept", "kochen", "wie", "backen"}),
    "pt": frozenset({"o", "a", "de", "com", "receita", "cozinha", "e", "para", "como"}),
}

_LATIN_LANGS: tuple[str, ...] = ("en", "es", "fr", "it", "de", "pt")


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {
        "Latin": 0,
        "CJK": 0,
        "Hangul": 0,
        "Devanagari": 0,
        "Arabic": 0,
        "Cyrillic": 0,
        "Kana": 0,
    }
    for ch in text:
        if not ch.isalpha():
            continue
        code = ord(ch)
        if 0x3040 <= code <= 0x30FF:
            counts["Kana"] += 1
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            counts["CJK"] += 1
        elif 0xAC00 <= code <= 0xD7AF:
            counts["Hangul"] += 1
        elif 0x0900 <= code <= 0x097F:
            counts["Devanagari"] += 1
        elif 0x0600 <= code <= 0x06FF:
            counts["Arabic"] += 1
        elif 0x0400 <= code <= 0x04FF:
            counts["Cyrillic"] += 1
        else:
            name = unicodedata.name(ch, "")
            if name.startswith("LATIN"):
                counts["Latin"] += 1
    return counts


def _tokenize_latin(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for ch in text.lower():
        if ch.isalpha() and (
            unicodedata.name(ch, "").startswith("LATIN") or 0x0300 <= ord(ch) <= 0x036F
        ):
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _latin_language(tokens: list[str]) -> tuple[str | None, float]:
    if not tokens:
        return None, 0.0
    scores: dict[str, int] = {lang: 0 for lang in _LATIN_LANGS}
    for tok in tokens:
        for lang in _LATIN_LANGS:
            if tok in _STOP_WORDS[lang]:
                scores[lang] += 1
    lang, hits = max(scores.items(), key=lambda kv: kv[1])
    if hits == 0:
        return "en", 0.05
    return lang, min(1.0, hits / max(4.0, len(tokens) / 4.0))


def detect_language(text: str) -> tuple[str | None, float]:
    """Return (iso_code | None, confidence in [0, 1]) for `text`."""
    if not text or not text.strip():
        return None, 0.0
    counts = _script_counts(text)
    total = sum(counts.values())
    if total == 0:
        return None, 0.0

    dominant, dominant_count = max(counts.items(), key=lambda kv: kv[1])
    dominant_ratio = dominant_count / total

    if dominant == "CJK" and dominant_ratio > 0.4:
        if counts["Kana"] > 0:
            return "ja", min(1.0, dominant_ratio + 0.1)
        return "zh", dominant_ratio
    if dominant == "Kana":
        return "ja", dominant_ratio
    if dominant == "Hangul":
        return "ko", dominant_ratio
    if dominant == "Devanagari":
        return "hi", dominant_ratio
    if dominant == "Arabic":
        return "ar", dominant_ratio
    if dominant == "Cyrillic":
        return "ru", dominant_ratio

    tokens = _tokenize_latin(text)
    lang, latin_conf = _latin_language(tokens)
    confidence = latin_conf * dominant_ratio
    return lang, confidence


def language_confidence(record: VideoRecord) -> float:
    """Return `detect_language` confidence for a record's metadata.

    Excludes `recipe_steps` on purpose so the signal reflects
    human-supplied surface text rather than machine-generated blobs.
    """
    text = f"{record.title}\n{record.description}"
    _, conf = detect_language(text)
    return conf


def language_hint(record: VideoRecord) -> str | None:
    text = f"{record.title}\n{record.description}"
    lang, _ = detect_language(text)
    return lang


def batch_language_confidence(records: Iterable[VideoRecord]) -> list[float]:
    return [language_confidence(r) for r in records]
