"""Deterministic, offline language detection — Latin-script, cooking-ish.

Scope: `{en, es, fr, de, it, pt}`. These are the five Western-European
languages with the heaviest cooking corpora on the open web (plus
English). CJK, Arabic, and other non-Latin scripts are explicitly
out of scope today and must land in a follow-up adversarial plan.

Algorithm:
  1. Tokenize on whitespace + light punctuation.
  2. Count function-word hits per language against small lexicons.
  3. Return the top language iff `(top_hits / total_tokens) >= THRESHOLD`
     *and* the margin over the runner-up is at least `MARGIN`.
  4. Otherwise return `None`. "Unsure" is a valid, honest answer.

The lexicons are intentionally tiny: this is a *gate*, not a classifier.
Any downstream code must still treat `language` as a hint, never truth.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

LATIN_LANGS: tuple[str, ...] = ("en", "es", "fr", "de", "it", "pt")

FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "a",
            "an",
            "and",
            "or",
            "of",
            "to",
            "in",
            "on",
            "with",
            "for",
            "is",
            "are",
            "was",
            "were",
            "this",
            "that",
            "it",
            "be",
            "add",
            "stir",
            "until",
            "then",
            "cook",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "un",
            "una",
            "y",
            "o",
            "de",
            "del",
            "en",
            "con",
            "para",
            "es",
            "son",
            "este",
            "esta",
            "por",
            "anadir",
            "hasta",
            "cocinar",
            "mezclar",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "de",
            "du",
            "dans",
            "avec",
            "pour",
            "est",
            "sont",
            "ce",
            "cette",
            "ajouter",
            "jusqu",
            "cuire",
            "melanger",
        }
    ),
    "de": frozenset(
        {
            "der",
            "die",
            "das",
            "ein",
            "eine",
            "und",
            "oder",
            "von",
            "zu",
            "in",
            "mit",
            "fur",
            "ist",
            "sind",
            "dies",
            "diese",
            "hinzufugen",
            "bis",
            "kochen",
            "mischen",
        }
    ),
    "it": frozenset(
        {
            "il",
            "la",
            "lo",
            "i",
            "gli",
            "le",
            "un",
            "una",
            "e",
            "o",
            "di",
            "del",
            "della",
            "in",
            "con",
            "per",
            "sono",
            "aggiungere",
            "fino",
            "cuocere",
            "mescolare",
        }
    ),
    "pt": frozenset(
        {
            "o",
            "a",
            "os",
            "as",
            "um",
            "uma",
            "e",
            "ou",
            "de",
            "do",
            "da",
            "em",
            "com",
            "para",
            "sao",
            "este",
            "esta",
            "adicionar",
            "ate",
            "cozinhar",
            "misturar",
        }
    ),
}

CONFIDENCE_THRESHOLD = 0.08
MARGIN = 1  # dominant language must have strictly more hits than the runner-up

_TOKEN_RE = re.compile(r"[A-Za-z\u00C0-\u024F]+")


def _normalise(text: str) -> list[str]:
    """Lowercase, ASCII-fold, tokenize. Returns a list of alpha tokens."""
    if not text:
        return []
    folded = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return [t.lower() for t in _TOKEN_RE.findall(ascii_only)]


def detect_language(text: str) -> str | None:
    """Return a BCP-47 code from `LATIN_LANGS`, or `None` if unsure."""
    tokens = _normalise(text)
    if len(tokens) < 4:
        return None

    hits: Counter[str] = Counter()
    for tok in tokens:
        for lang, lex in FUNCTION_WORDS.items():
            if tok in lex:
                hits[lang] += 1

    if not hits:
        return None

    (top_lang, top_hits), *rest = hits.most_common(2)
    runner_up = rest[0][1] if rest else 0

    if top_hits - runner_up < MARGIN:
        return None
    if top_hits / len(tokens) < CONFIDENCE_THRESHOLD:
        return None
    return top_lang
