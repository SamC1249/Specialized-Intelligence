"""Dependency-free language detection.

Two signals combined:

  1. **Script detection** — count characters from Unicode ranges of
     Latin, Cyrillic, CJK (Han/Hiragana/Katakana/Hangul), Arabic,
     Hebrew, Devanagari, Greek, Thai. If a single non-Latin script
     dominates by >= 50% of alphabetic characters, we return a coarse
     script tag (`zh` / `ja` / `ko` / `ar` / `hi` / `ru` / ...). This
     lets us keep multilingual CC-clean records without misrouting
     everything into `"unknown"`.

  2. **Function-word / n-gram voting** — for Latin-script strings, we
     score against a small dictionary of ~15 highly-frequent tokens per
     language (en / es / fr / de / it / pt / nl / pl). The language
     with the most hits wins if >= 2 hits and > 2x the runner-up.

Both signals are *heuristic*. They are never allowed to affect the
`redistributable` decision (which is a licensing question). They only
feed the quality scorer and let us bucket records for stratified
sampling.

Returns a BCP-47 code (`en`, `fr`, ...) or `None` when neither signal
is confident enough.
"""

from __future__ import annotations

import re
import unicodedata

_ALPHA_RE = re.compile(r"\w+", re.UNICODE)

# Ranges chosen to cover the "content-bearing" characters we care about.
_SCRIPT_RANGES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("zh", (0x4E00, 0x9FFF)),
    ("zh", (0x3400, 0x4DBF)),
    ("ja", (0x3040, 0x309F)),  # hiragana
    ("ja", (0x30A0, 0x30FF)),  # katakana
    ("ko", (0xAC00, 0xD7AF)),
    ("ar", (0x0600, 0x06FF)),
    ("he", (0x0590, 0x05FF)),
    ("hi", (0x0900, 0x097F)),
    ("ru", (0x0400, 0x04FF)),  # Cyrillic, coarse -> ru
    ("el", (0x0370, 0x03FF)),
    ("th", (0x0E00, 0x0E7F)),
)

# Order matters only for tie-breaking (list index breaks equal-hit ties).
_STOPWORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "the",
        "and",
        "with",
        "for",
        "into",
        "over",
        "recipe",
        "cooking",
        "add",
        "stir",
        "then",
        "until",
        "step",
        "minutes",
        "sauce",
    ),
    "es": (
        "el",
        "la",
        "de",
        "con",
        "para",
        "sobre",
        "receta",
        "cocina",
        "añadir",
        "hasta",
        "paso",
        "minutos",
        "salsa",
        "y",
        "los",
    ),
    "fr": (
        "le",
        "la",
        "et",
        "avec",
        "pour",
        "dans",
        "recette",
        "cuisine",
        "ajouter",
        "jusqu",
        "étape",
        "minutes",
        "sauce",
        "les",
        "des",
    ),
    "de": (
        "der",
        "die",
        "das",
        "und",
        "mit",
        "für",
        "über",
        "rezept",
        "kochen",
        "hinzufügen",
        "bis",
        "schritt",
        "minuten",
        "soße",
        "eine",
    ),
    "it": (
        "il",
        "la",
        "e",
        "con",
        "per",
        "sopra",
        "ricetta",
        "cucina",
        "aggiungere",
        "fino",
        "passo",
        "minuti",
        "salsa",
        "le",
        "gli",
    ),
    "pt": (
        "o",
        "a",
        "e",
        "com",
        "para",
        "sobre",
        "receita",
        "cozinha",
        "adicionar",
        "até",
        "passo",
        "minutos",
        "molho",
        "os",
        "as",
    ),
    "nl": (
        "de",
        "het",
        "en",
        "met",
        "voor",
        "over",
        "recept",
        "koken",
        "toevoegen",
        "tot",
        "stap",
        "minuten",
        "saus",
        "een",
        "van",
    ),
    "pl": (
        "i",
        "z",
        "na",
        "do",
        "przepis",
        "gotowanie",
        "dodać",
        "krok",
        "minut",
        "sos",
        "oraz",
        "dla",
        "ze",
        "przez",
        "który",
    ),
}


def _script_vote(text: str) -> tuple[str | None, int, int]:
    counts: dict[str, int] = {}
    total_alpha = 0
    for ch in text:
        if not ch.isalpha():
            continue
        total_alpha += 1
        code = ord(ch)
        for lang, (lo, hi) in _SCRIPT_RANGES:
            if lo <= code <= hi:
                counts[lang] = counts.get(lang, 0) + 1
                break
    if not counts or total_alpha == 0:
        return None, 0, total_alpha
    lang, hits = max(counts.items(), key=lambda kv: kv[1])
    return lang, hits, total_alpha


def _tokens(text: str) -> list[str]:
    return [unicodedata.normalize("NFKC", m.group(0)).lower() for m in _ALPHA_RE.finditer(text)]


def _stopword_vote(text: str) -> tuple[str | None, int, int]:
    tokens = set(_tokens(text))
    if not tokens:
        return None, 0, 0
    scores: list[tuple[int, str]] = []
    for lang, words in _STOPWORDS.items():
        scores.append((sum(1 for w in words if w in tokens), lang))
    scores.sort(reverse=True)
    top_hits, top_lang = scores[0]
    runner_up_hits = scores[1][0] if len(scores) > 1 else 0
    if top_hits >= 2 and top_hits > 2 * runner_up_hits:
        return top_lang, top_hits, len(tokens)
    return None, top_hits, len(tokens)


def detect_language(*texts: str) -> str | None:
    """Return a BCP-47 code (`en`, `fr`, ...) or `None` if unsure."""
    joined = " ".join(t for t in texts if t)
    if not joined.strip():
        return None

    script_lang, script_hits, total_alpha = _script_vote(joined)
    if script_lang and total_alpha > 0 and script_hits / total_alpha >= 0.5:
        return script_lang

    stop_lang, _, _ = _stopword_vote(joined)
    return stop_lang


def is_confidently_tagged(*texts: str) -> bool:
    return detect_language(*texts) is not None
