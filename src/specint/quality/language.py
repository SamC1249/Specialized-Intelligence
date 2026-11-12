"""Metadata-only language detection.

Tiny, dependency-free detector used to tag `VideoRecord.language` when the
upstream did not provide one. The function is intentionally conservative:
it returns `None` rather than guess on very short / ambiguous text.

Strategy (checked in this order):
  1. Unicode-range check for scripts that uniquely identify a language
     family: CJK Han (zh/ja), Hiragana/Katakana (ja), Hangul (ko),
     Devanagari (hi), Cyrillic (ru), Arabic (ar).
  2. Stopword hit count for Latin-script languages (en, es, fr, de, it,
     pt, nl). The language with the highest hit count wins, provided
     the winner has at least `MIN_STOPWORD_HITS` matches.

Stopword lists are the ~25 most frequent function words per language,
taken from publicly-available frequency lists (Leipzig Corpora Collection
derivatives). They are not intended to compete with fastText; they exist
so we can compute per-language yield offline, in CI, without adding a
runtime dependency.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# BCP-47 tags we emit.
EN, ES, FR, DE, IT, PT, NL = "en", "es", "fr", "de", "it", "pt", "nl"
ZH, JA, KO, HI, RU, AR = "zh", "ja", "ko", "hi", "ru", "ar"

MIN_STOPWORD_HITS = 2

_LATIN_STOPWORDS: dict[str, frozenset[str]] = {
    EN: frozenset(
        [
            "the",
            "of",
            "and",
            "to",
            "a",
            "in",
            "is",
            "it",
            "you",
            "that",
            "he",
            "was",
            "for",
            "on",
            "are",
            "with",
            "as",
            "i",
            "his",
            "they",
            "be",
            "at",
            "one",
            "have",
            "this",
            "from",
            "or",
            "had",
            "by",
        ]
    ),
    ES: frozenset(
        [
            "el",
            "la",
            "de",
            "que",
            "y",
            "a",
            "en",
            "los",
            "se",
            "del",
            "las",
            "por",
            "un",
            "para",
            "con",
            "no",
            "una",
            "su",
            "al",
            "lo",
            "como",
            "más",
            "pero",
            "sus",
            "le",
            "ya",
            "o",
            "este",
            "sí",
        ]
    ),
    FR: frozenset(
        [
            "le",
            "la",
            "de",
            "et",
            "à",
            "les",
            "des",
            "un",
            "une",
            "du",
            "en",
            "que",
            "pour",
            "dans",
            "qui",
            "est",
            "ne",
            "pas",
            "sur",
            "au",
            "avec",
            "son",
            "plus",
            "ou",
            "il",
            "elle",
            "ce",
            "se",
        ]
    ),
    DE: frozenset(
        [
            "der",
            "die",
            "und",
            "in",
            "den",
            "von",
            "zu",
            "das",
            "mit",
            "sich",
            "des",
            "auf",
            "für",
            "ist",
            "im",
            "dem",
            "nicht",
            "ein",
            "eine",
            "als",
            "auch",
            "es",
            "an",
            "werden",
            "aus",
            "er",
            "hat",
        ]
    ),
    IT: frozenset(
        [
            "il",
            "di",
            "che",
            "e",
            "la",
            "a",
            "un",
            "in",
            "per",
            "i",
            "una",
            "del",
            "è",
            "non",
            "con",
            "la",
            "si",
            "da",
            "le",
            "mi",
            "ma",
            "al",
            "come",
            "se",
            "della",
            "lo",
            "gli",
            "alla",
        ]
    ),
    PT: frozenset(
        [
            "de",
            "a",
            "o",
            "que",
            "e",
            "do",
            "da",
            "em",
            "um",
            "para",
            "com",
            "não",
            "uma",
            "os",
            "no",
            "se",
            "na",
            "por",
            "mais",
            "as",
            "dos",
            "como",
            "mas",
            "ao",
            "ele",
            "das",
            "à",
            "seu",
        ]
    ),
    NL: frozenset(
        [
            "de",
            "het",
            "een",
            "en",
            "van",
            "ik",
            "te",
            "dat",
            "die",
            "in",
            "op",
            "voor",
            "met",
            "als",
            "zijn",
            "er",
            "maar",
            "om",
            "hem",
            "ze",
            "dan",
            "je",
            "nu",
            "over",
            "mij",
        ]
    ),
}


def _has_script(text: str, ranges: Iterable[tuple[int, int]]) -> bool:
    for ch in text:
        cp = ord(ch)
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return True
    return False


# Unicode-range signatures (ordered: more specific first).
_HIRAGANA_KATAKANA = ((0x3040, 0x30FF),)
_HANGUL = ((0xAC00, 0xD7AF), (0x1100, 0x11FF))
_CJK_HAN = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF))
_DEVANAGARI = ((0x0900, 0x097F),)
_CYRILLIC = ((0x0400, 0x04FF),)
_ARABIC = ((0x0600, 0x06FF), (0x0750, 0x077F))


_WORD_RE = re.compile(r"[a-záéíóúñüàâäçèéêëîïôöùûüœœßäöüàáâãäçèéêëíìîïòóôõöùúûü]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKC", text).lower()
    return _WORD_RE.findall(folded)


def detect_language(text: str) -> str | None:
    """Return a BCP-47 code (or `None`) for `text`. Pure, deterministic."""
    if not text or len(text.strip()) < 3:
        return None

    if _has_script(text, _HIRAGANA_KATAKANA):
        return JA
    if _has_script(text, _HANGUL):
        return KO
    if _has_script(text, _CJK_HAN):
        return ZH  # ja without kana is rare but possible; caller can override
    if _has_script(text, _DEVANAGARI):
        return HI
    if _has_script(text, _ARABIC):
        return AR
    if _has_script(text, _CYRILLIC):
        return RU

    tokens = _tokenize(text)
    if not tokens:
        return None
    best_lang: str | None = None
    best_hits = 0
    for lang, stopwords in _LATIN_STOPWORDS.items():
        hits = sum(1 for tok in tokens if tok in stopwords)
        if hits > best_hits:
            best_hits = hits
            best_lang = lang
    if best_hits >= MIN_STOPWORD_HITS:
        return best_lang
    return None
