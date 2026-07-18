"""Offline heuristic language detection.

Deliberately dependency-free. Two-stage classifier:

  1. Script detection by Unicode range: if the text is dominated by
     Hiragana/Katakana it's `ja`; CJK ideographs → `zh` (fallback,
     since we cannot disambiguate zh vs. ja from Han alone); Hangul → `ko`;
     Cyrillic → `ru`; Devanagari → `hi`; Arabic → `ar`.
  2. Latin-script disambiguation by a tiny stopword bag per language.
     Whichever stopword set has the highest per-token hit rate wins,
     provided it clears a minimum absolute-hit threshold. Otherwise
     we return `None` (never guess).

Everything is pure, deterministic, and unit-tested against short strings
so that the harness can annotate `record.language` without touching the
network. This is intentionally *not* a replacement for a real detector
like fasttext — we only want a signal cheap enough to run over millions
of candidate records before download.
"""

from __future__ import annotations

import re
import unicodedata

_LATIN_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "cooking",
            "recipe",
            "cook",
            "video",
            "how",
            "to",
            "of",
            "a",
            "in",
            "is",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "que",
            "para",
            "con",
            "cocina",
            "receta",
            "cocinar",
            "video",
            "como",
            "y",
            "un",
            "una",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "de",
            "des",
            "pour",
            "avec",
            "cuisine",
            "recette",
            "cuisiner",
            "video",
            "vidéo",
            "comment",
            "et",
            "un",
            "une",
        }
    ),
    "de": frozenset(
        {
            "der",
            "die",
            "das",
            "und",
            "mit",
            "für",
            "kochen",
            "rezept",
            "video",
            "wie",
            "ein",
            "eine",
            "ist",
            "auf",
            "zum",
        }
    ),
    "it": frozenset(
        {
            "il",
            "la",
            "lo",
            "gli",
            "le",
            "di",
            "che",
            "per",
            "con",
            "cucina",
            "ricetta",
            "cucinare",
            "video",
            "come",
            "un",
            "una",
        }
    ),
    "pt": frozenset(
        {
            "o",
            "a",
            "os",
            "as",
            "de",
            "que",
            "para",
            "com",
            "cozinha",
            "receita",
            "cozinhar",
            "video",
            "vídeo",
            "como",
            "um",
            "uma",
        }
    ),
}

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", flags=re.UNICODE)


_UNIQUE_SCRIPTS = {"HIRAGANA": "ja", "KATAKANA": "ja", "HANGUL": "ko", "DEVANAGARI": "hi"}


def _script_signal(text: str) -> str | None:
    """Return an ISO-639-1 code when a non-Latin script signal is present.

    - Hiragana / Katakana / Hangul / Devanagari uniquely identify a language,
      so *any* presence is enough.
    - Cyrillic, Arabic, and CJK ideographs must dominate (>=30% of alpha
      characters) to avoid mislabelling loanwords and quoted text.
    """
    unique_hits: dict[str, int] = {}
    ambiguous: dict[str, int] = {}
    total = 0
    for ch in text:
        if ch.isspace() or not ch.isalpha():
            continue
        total += 1
        try:
            name = unicodedata.name(ch, "")
        except ValueError:
            continue
        matched_unique = False
        for token, lang in _UNIQUE_SCRIPTS.items():
            if token in name:
                unique_hits[lang] = unique_hits.get(lang, 0) + 1
                matched_unique = True
                break
        if matched_unique:
            continue
        if "CYRILLIC" in name:
            ambiguous["ru"] = ambiguous.get("ru", 0) + 1
        elif "ARABIC" in name:
            ambiguous["ar"] = ambiguous.get("ar", 0) + 1
        elif "CJK UNIFIED IDEOGRAPH" in name:
            ambiguous["zh"] = ambiguous.get("zh", 0) + 1
    if unique_hits:
        return max(unique_hits.items(), key=lambda kv: kv[1])[0]
    if not total or not ambiguous:
        return None
    best_lang, best_count = max(ambiguous.items(), key=lambda kv: kv[1])
    if best_count / total < 0.30:
        return None
    return best_lang


def _latin_signal(text: str) -> str | None:
    tokens = [t.casefold() for t in _TOKEN_RE.findall(text)]
    if len(tokens) < 3:
        return None
    scores: dict[str, int] = {}
    for lang, stops in _LATIN_STOPWORDS.items():
        scores[lang] = sum(1 for t in tokens if t in stops)
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < 2:
        return None
    others = [s for lang, s in scores.items() if lang != best_lang]
    if others and best_score <= max(others):
        return None
    return best_lang


def detect_language(text: str) -> str | None:
    """Return an ISO-639-1 code or `None` when confidence is insufficient."""
    if not text or not text.strip():
        return None
    script = _script_signal(text)
    if script:
        return script
    return _latin_signal(text)


def annotate_language(title: str, description: str, current: str | None) -> str | None:
    """Only fill missing `language`; never override an upstream-declared one."""
    if current:
        return current
    return detect_language(f"{title} {description}")
