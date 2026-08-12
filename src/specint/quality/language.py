"""Metadata-only language detection.

Zero-dependency heuristic: dominant unicode script + tiny stopword
lookup. Returns a BCP-47-ish tag or `None` when the signal is too
weak. Deliberately narrow — we only need to distinguish the small set
of languages the current seed queries plausibly hit (en, es, fr, de,
it, pt, ja, zh, ko, ru, ar, hi). A misfire returns `None`, never a
wrong guess.

Not a general-purpose language ID. If accuracy on the fixtures ever
drops below the target in `docs/plan-2026-08-12.md` we should replace
this with a pretrained model rather than layering more regexes.
"""

from __future__ import annotations

import re
from collections import Counter

_STOPWORDS: dict[str, set[str]] = {
    "en": {
        "the",
        "and",
        "with",
        "for",
        "recipe",
        "cooking",
        "how",
        "to",
        "of",
        "a",
        "an",
        "in",
        "on",
        "is",
        "make",
        "easy",
        "best",
    },
    "es": {
        "la",
        "el",
        "de",
        "con",
        "receta",
        "cocina",
        "para",
        "como",
        "los",
        "las",
        "y",
        "en",
        "hacer",
        "casero",
        "facil",
    },
    "fr": {
        "la",
        "le",
        "de",
        "des",
        "avec",
        "recette",
        "cuisine",
        "pour",
        "comment",
        "les",
        "et",
        "en",
        "au",
    },
    "de": {
        "der",
        "die",
        "das",
        "mit",
        "rezept",
        "kochen",
        "wie",
        "und",
        "ein",
        "eine",
        "im",
        "zu",
    },
    "it": {
        "la",
        "il",
        "di",
        "con",
        "ricetta",
        "cucina",
        "per",
        "come",
        "gli",
        "le",
        "e",
        "in",
    },
    "pt": {
        "a",
        "o",
        "de",
        "com",
        "receita",
        "cozinha",
        "para",
        "como",
        "os",
        "as",
        "e",
        "em",
    },
    "ru": {"как", "рецепт", "и", "с", "для", "готовить", "на"},  # noqa: RUF001
}

_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def _has_kana(text: str) -> bool:
    return any(0x3040 <= ord(c) <= 0x30FF for c in text)


def _script_hint(text: str) -> str | None:
    """Return a BCP-47 tag when the text is dominated by a non-Latin script."""

    if not text:
        return None
    has_kana = _has_kana(text)
    counts: Counter[str] = Counter()
    for ch in text:
        code = ord(ch)
        if 0x3040 <= code <= 0x30FF:
            counts["ja"] += 1
        elif 0x4E00 <= code <= 0x9FFF:
            counts["ja" if has_kana else "zh"] += 1
        elif 0xAC00 <= code <= 0xD7AF:
            counts["ko"] += 1
        elif 0x0400 <= code <= 0x04FF:
            counts["ru"] += 1
        elif 0x0600 <= code <= 0x06FF:
            counts["ar"] += 1
        elif 0x0900 <= code <= 0x097F:
            counts["hi"] += 1
    if not counts:
        return None
    top, top_count = counts.most_common(1)[0]
    letters = sum(1 for ch in text if ch.isalpha())
    if letters and top_count / letters >= 0.3:
        return top
    return None


def detect_language(text: str) -> str | None:
    """Return best-guess BCP-47 tag, or `None` when signal is too weak."""

    if not text or not text.strip():
        return None

    script = _script_hint(text)
    if script is not None:
        return script

    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return None
    scores: Counter[str] = Counter()
    for tok in tokens:
        for lang, words in _STOPWORDS.items():
            if tok in words:
                scores[lang] += 1
    if not scores:
        return None
    top, top_count = scores.most_common(1)[0]
    if top_count < 2 and len(tokens) > 6:
        return None
    return top
