"""Metadata-only language detection.

Deliberately *zero-dependency* and *pure*: given a short piece of text
(typically a title + description), return a coarse ISO 639-1 language
code and a confidence in [0, 1].

The heuristic combines two signals:

1. **Unicode range coverage.** Text dominated by CJK-Unified /
   Hiragana / Katakana / Hangul / Arabic / Cyrillic / Devanagari code
   points is labelled by script.
2. **Stop-word lookup.** For Latin-script languages we compare a tiny
   curated stop-word set (top ~20 function words) and score by the
   fraction of tokens that hit.

Confidence caveats (surfaced verbatim to callers):
- Short titles (< 3 tokens) are inherently noisy; confidence caps at
  0.5 for Latin-script decisions on such inputs.
- Transliterated words (e.g. "sushi" in an English sentence) will not
  flip the detector — the stop-word signal dominates.

This module never raises; malformed input returns `(None, 0.0)`.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

# Stop-word lexicons are intentionally short (top function words). We
# only need to *discriminate* the languages we care about for cooking
# corpora, not to translate them.
STOP_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "and",
            "a",
            "an",
            "of",
            "to",
            "in",
            "on",
            "with",
            "for",
            "is",
            "it",
            "this",
            "that",
            "how",
            "you",
            "your",
            "make",
            "add",
            "cook",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "y",
            "en",
            "un",
            "una",
            "con",
            "para",
            "que",
            "por",
            "es",
            "como",
            "esto",
            "receta",
            "cocina",
            "hacer",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "de",
            "des",
            "et",
            "en",
            "un",
            "une",
            "avec",
            "pour",
            "que",
            "par",
            "est",
            "comment",
            "vous",
            "votre",
            "recette",
            "cuisine",
            "faire",
        }
    ),
    "de": frozenset(
        {
            "der",
            "die",
            "das",
            "und",
            "in",
            "im",
            "mit",
            "für",
            "ein",
            "eine",
            "ist",
            "wie",
            "sie",
            "ihr",
            "rezept",
            "kochen",
            "koch",
            "machen",
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
            "del",
            "e",
            "in",
            "con",
            "per",
            "che",
            "come",
            "voi",
            "vostro",
            "ricetta",
            "cucina",
            "fare",
        }
    ),
    "pt": frozenset(
        {
            "o",
            "a",
            "os",
            "as",
            "de",
            "do",
            "da",
            "e",
            "em",
            "com",
            "para",
            "que",
            "por",
            "é",
            "como",
            "você",
            "seu",
            "receita",
            "cozinha",
            "fazer",
        }
    ),
}

# Order matters for tie-breaking; keep deterministic.
_LATIN_LANGS = ("en", "es", "fr", "de", "it", "pt")

# Script-family markers → ISO 639-1 (best-effort — a single script may
# be shared, e.g. Devanagari is used by Hindi and Marathi).
_SCRIPT_TO_LANG: dict[str, str] = {
    "HIRAGANA": "ja",
    "KATAKANA": "ja",
    "HANGUL": "ko",
    "CJK": "zh",  # ambiguous with ja; hiragana/katakana take precedence
    "ARABIC": "ar",
    "CYRILLIC": "ru",
    "DEVANAGARI": "hi",
}


def _script_family(codepoint: str) -> str | None:
    if not codepoint:
        return None
    try:
        name = unicodedata.name(codepoint)
    except ValueError:
        return None
    if "HIRAGANA" in name:
        return "HIRAGANA"
    if "KATAKANA" in name:
        return "KATAKANA"
    if "HANGUL" in name:
        return "HANGUL"
    if name.startswith("CJK "):
        return "CJK"
    if "ARABIC" in name:
        return "ARABIC"
    if "CYRILLIC" in name:
        return "CYRILLIC"
    if "DEVANAGARI" in name:
        return "DEVANAGARI"
    if "LATIN" in name:
        return "LATIN"
    return None


def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    cur: list[str] = []
    for ch in text.lower():
        if ch.isalpha() or ch == "'":
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        fam = _script_family(ch)
        if fam:
            counts[fam] = counts.get(fam, 0) + 1
    return counts


def detect_language(text: str | None) -> tuple[str | None, float]:
    """Return `(iso_code, confidence)` for `text`.

    `iso_code` is a two-letter ISO 639-1 code (`en`, `ja`, ...) or
    `None` when the text is empty / undetectable. `confidence` is
    always in [0, 1]. Callers should use it as a *hint*: filtering
    downstream corpora on a hard threshold will drop legitimate
    records.
    """
    if not text or not isinstance(text, str):
        return None, 0.0

    text = text.strip()
    if not text:
        return None, 0.0

    counts = _script_counts(text)
    non_latin_letters = sum(v for k, v in counts.items() if k != "LATIN")
    total_letters = sum(counts.values())

    if total_letters == 0:
        return None, 0.0

    # Non-Latin scripts short-circuit: their presence is a very strong
    # signal even for short inputs.
    if non_latin_letters > 0:
        kana = counts.get("HIRAGANA", 0) + counts.get("KATAKANA", 0)
        if kana > 0:
            share = (kana + counts.get("CJK", 0)) / total_letters
            return "ja", min(1.0, 0.6 + 0.4 * share)
        best_script = max((k for k in counts if k != "LATIN"), key=lambda k: counts[k])
        lang = _SCRIPT_TO_LANG.get(best_script)
        share = counts[best_script] / total_letters
        return lang, min(1.0, 0.6 + 0.4 * share)

    tokens = _tokenize(text)
    if not tokens:
        return None, 0.0

    best_lang: str | None = None
    best_hits = 0
    for lang in _LATIN_LANGS:
        stops = STOP_WORDS[lang]
        hits = sum(1 for t in tokens if t in stops)
        if hits > best_hits:
            best_hits = hits
            best_lang = lang

    if best_hits == 0:
        return None, 0.15

    ratio = best_hits / max(1, len(tokens))
    conf = 0.4 + 0.5 * ratio
    if len(tokens) < 3:
        conf = min(conf, 0.5)
    return best_lang, min(1.0, conf)


def matches_target(text: str | None, target: str | None) -> float:
    """Return a soft [0, 1] match score against a requested language.

    - `target` `None` → 1.0 (no filter).
    - Detected language matches `target` → confidence.
    - Detected language differs → `1.0 - confidence` (so a strong
      wrong-language signal produces a low score, but a *weak* signal
      still gives partial credit and doesn't nuke the record).
    """
    if not target:
        return 1.0
    lang, conf = detect_language(text)
    if lang is None:
        return 0.5
    if lang == target:
        return conf
    return max(0.0, 1.0 - conf)


def summarise(texts: Iterable[str]) -> dict[str, float]:
    """Aggregate: for a batch of texts, mean confidence per language."""
    per_lang: dict[str, list[float]] = {}
    for t in texts:
        lang, conf = detect_language(t)
        if lang is None:
            continue
        per_lang.setdefault(lang, []).append(conf)
    return {k: sum(v) / len(v) for k, v in per_lang.items()}
