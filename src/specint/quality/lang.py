"""Cheap, deterministic language detection.

Two-tier heuristic, no external dependency:

1. **Unicode-block prior.** If ≥40% of alphabetic characters fall in a
   non-Latin block, we return the block's canonical BCP-47 tag
   (Cyrillic → "ru", CJK Unified Ideographs → "zh", Hiragana/Katakana
   → "ja", Hangul → "ko", Arabic → "ar", Devanagari → "hi",
   Greek → "el", Hebrew → "he", Thai → "th"). This resolves the
   overwhelming majority of clearly-non-English cases without any
   further work.

2. **Stopword vote.** For Latin-script text we tokenise on whitespace
   + punctuation, lowercase, and count matches against a *tiny*
   stopword table for {en, es, fr, de, it, pt, nl}. The language with
   the highest count wins provided the count is ≥ 2; otherwise return
   `None` (unknown).

This is deliberately biased toward *precision over recall*: we would
much rather emit `None` and downweight the record than mislabel it.
Downstream models can always re-run a heavier detector on the shortlist
we produce.

`detect_language` accepts any str and returns a BCP-47 tag or `None`.
`detect_from_record(record)` concatenates `title + " " + description`
(deduplicating identical values) and calls the same detector.
"""

from __future__ import annotations

import re
import unicodedata

from specint.records import VideoRecord

_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "and",
            "of",
            "to",
            "in",
            "a",
            "is",
            "for",
            "with",
            "on",
            "you",
            "how",
            "recipe",
            "cook",
            "cooking",
        }
    ),
    "es": frozenset({"el", "la", "los", "las", "de", "y", "con", "para", "una", "receta"}),
    "fr": frozenset({"le", "la", "les", "de", "et", "avec", "pour", "une", "recette", "cuisine"}),
    "de": frozenset({"der", "die", "das", "und", "mit", "für", "ein", "eine", "rezept", "kochen"}),
    "it": frozenset({"il", "la", "lo", "gli", "e", "con", "per", "una", "ricetta", "cucina"}),
    "pt": frozenset({"o", "a", "os", "as", "de", "e", "com", "para", "uma", "receita", "cozinha"}),
    "nl": frozenset({"de", "het", "en", "van", "met", "voor", "een", "recept", "koken"}),
}

_BLOCK_TO_LANG: tuple[tuple[str, str], ...] = (
    ("CYRILLIC", "ru"),
    ("HIRAGANA", "ja"),
    ("KATAKANA", "ja"),
    ("CJK UNIFIED IDEOGRAPH", "zh"),
    ("HANGUL", "ko"),
    ("ARABIC", "ar"),
    ("DEVANAGARI", "hi"),
    ("GREEK", "el"),
    ("HEBREW", "he"),
    ("THAI", "th"),
)

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")


def _script_hit(ch: str) -> str | None:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    for prefix, tag in _BLOCK_TO_LANG:
        if name.startswith(prefix):
            return tag
    return None


def detect_language(text: str) -> str | None:
    if not text:
        return None
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return None

    counts: dict[str, int] = {}
    for c in alpha:
        tag = _script_hit(c)
        if tag:
            counts[tag] = counts.get(tag, 0) + 1
    if counts:
        top_tag, top_count = max(counts.items(), key=lambda kv: kv[1])
        if top_count / len(alpha) >= 0.4:
            return top_tag

    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return None
    votes: dict[str, int] = {}
    for tok in tokens:
        for lang, sw in _STOPWORDS.items():
            if tok in sw:
                votes[lang] = votes.get(lang, 0) + 1
    if not votes:
        return None
    top_lang, top_votes = max(votes.items(), key=lambda kv: kv[1])
    return top_lang if top_votes >= 2 else None


def detect_from_record(record: VideoRecord) -> str | None:
    parts = [record.title]
    if record.description and record.description != record.title:
        parts.append(record.description)
    return detect_language(" ".join(p for p in parts if p))
