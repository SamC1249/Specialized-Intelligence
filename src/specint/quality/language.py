"""Offline BCP-47 language detection.

Heuristic-only: counts stop-word overlaps and a handful of character
signatures. Purely offline (no external dependencies), deterministic,
and fast — the goal is to bucket titles+descriptions into a coarse
language so we can (a) prioritise crawls in languages we currently
under-serve and (b) filter noise like "test upload" from real content.

Not a replacement for `cld3`/`fasttext` at scale. The intent is a
metadata-only scorer that we can run on millions of records before
committing to a heavier extractor.

Supported languages (BCP-47 primary tags):
  en, es, fr, de, it, pt, nl.

Returns ``None`` when there is not enough evidence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[a-zà-ÿA-ZÀ-Ÿ']+")

_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        [
            "the",
            "a",
            "an",
            "and",
            "or",
            "of",
            "to",
            "in",
            "for",
            "on",
            "with",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "by",
            "from",
            "that",
            "this",
            "it",
            "as",
            "at",
            "not",
        ]
    ),
    "es": frozenset(
        [
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "y",
            "o",
            "en",
            "para",
            "con",
            "un",
            "una",
            "es",
            "está",
            "esta",
            "este",
            "ese",
            "esa",
            "por",
            "sin",
            "sobre",
            "entre",
        ]
    ),
    "fr": frozenset(
        [
            "le",
            "la",
            "les",
            "des",
            "de",
            "du",
            "et",
            "ou",
            "en",
            "pour",
            "avec",
            "un",
            "une",
            "est",
            "sont",
            "ce",
            "cette",
            "dans",
            "sur",
            "sans",
            "par",
            "au",
            "aux",
        ]
    ),
    "de": frozenset(
        [
            "der",
            "die",
            "das",
            "den",
            "dem",
            "ein",
            "eine",
            "einer",
            "und",
            "oder",
            "in",
            "für",
            "mit",
            "ist",
            "sind",
            "auf",
            "im",
            "am",
            "zu",
            "von",
            "bei",
            "über",
        ]
    ),
    "it": frozenset(
        [
            "il",
            "la",
            "lo",
            "gli",
            "le",
            "dei",
            "degli",
            "delle",
            "di",
            "del",
            "e",
            "o",
            "in",
            "per",
            "con",
            "un",
            "una",
            "uno",
            "è",
            "sono",
            "che",
            "questo",
            "quello",
        ]
    ),
    "pt": frozenset(
        [
            "o",
            "a",
            "os",
            "as",
            "um",
            "uma",
            "de",
            "do",
            "da",
            "dos",
            "das",
            "e",
            "ou",
            "em",
            "para",
            "com",
            "é",
            "são",
            "este",
            "esse",
            "esta",
            "essa",
            "por",
            "sem",
            "sobre",
        ]
    ),
    "nl": frozenset(
        [
            "de",
            "het",
            "een",
            "en",
            "of",
            "van",
            "voor",
            "met",
            "is",
            "zijn",
            "was",
            "waren",
            "in",
            "op",
            "aan",
            "bij",
            "door",
            "om",
            "te",
            "dat",
            "dit",
            "die",
        ]
    ),
}


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def detect_language(*fragments: str | None) -> str | None:
    """Return a BCP-47 primary tag, or None if unknown / insufficient text."""

    joined = " ".join(f for f in fragments if f)
    tokens = _tokens(joined)
    if len(tokens) < 4:
        return None

    scores: dict[str, int] = {}
    for lang, words in _STOPWORDS.items():
        scores[lang] = sum(1 for t in tokens if t in words)

    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score == 0:
        return None

    # Require the top language to beat the runner-up by at least one
    # stopword hit and account for >= 5% of tokens, else treat as unknown.
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 1:
        return None
    if best_score / max(len(tokens), 1) < 0.05:
        return None
    return best_lang


def classify_batch(fragments_iter: Iterable[tuple[str | None, ...]]) -> list[str | None]:
    return [detect_language(*frags) for frags in fragments_iter]
