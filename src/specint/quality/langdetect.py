"""Stoplist-based language detector.

Not a Unicode-aware n-gram model — just a curated stop-word list per
language. Good enough to backfill `record.language` when upstream
metadata is missing (Wikimedia titles are often un-tagged, PeerTube
returns `null`), so downstream filters like "keep en/es/fr only" work
without pulling in `langdetect`/`fasttext`.

Detection is a max-vote count over lowercased tokens; ties break in the
order of `SUPPORTED_LANGS`. Below `MIN_HITS`, returns `None`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

SUPPORTED_LANGS: tuple[str, ...] = ("en", "es", "fr", "de", "it", "pt", "ja")

STOP_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "and",
            "with",
            "for",
            "of",
            "in",
            "on",
            "to",
            "a",
            "an",
            "is",
            "are",
            "how",
            "recipe",
            "cooking",
            "video",
            "make",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "con",
            "para",
            "y",
            "en",
            "una",
            "un",
            "cómo",
            "receta",
            "cocina",
            "video",
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
            "avec",
            "pour",
            "et",
            "en",
            "un",
            "une",
            "comment",
            "recette",
            "cuisine",
            "vidéo",
            "faire",
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
            "in",
            "im",
            "ein",
            "eine",
            "wie",
            "rezept",
            "kochen",
            "video",
            "machen",
        }
    ),
    "it": frozenset(
        {
            "il",
            "la",
            "gli",
            "le",
            "di",
            "con",
            "per",
            "e",
            "in",
            "un",
            "una",
            "come",
            "ricetta",
            "cucina",
            "video",
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
            "com",
            "para",
            "e",
            "em",
            "um",
            "uma",
            "como",
            "receita",
            "cozinha",
            "vídeo",
            "fazer",
        }
    ),
    "ja": frozenset({"料理", "レシピ", "の", "を", "は", "が", "作り方"}),
}

MIN_HITS = 2

_TOKEN_RE = re.compile(r"[\w]+", flags=re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def detect(text: str) -> str | None:
    if not text:
        return None
    toks = _tokens(text)
    if not toks:
        return None
    scores: dict[str, int] = {lang: 0 for lang in SUPPORTED_LANGS}
    for t in toks:
        for lang in SUPPORTED_LANGS:
            if t in STOP_WORDS[lang]:
                scores[lang] += 1
    best_lang = max(SUPPORTED_LANGS, key=lambda lang: (scores[lang], -SUPPORTED_LANGS.index(lang)))
    return best_lang if scores[best_lang] >= MIN_HITS else None


def backfill_languages(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    out: list[VideoRecord] = []
    for r in records:
        if r.language:
            out.append(r)
            continue
        text = " ".join([r.title or "", r.description or "", *r.recipe_steps])
        guess = detect(text)
        if guess:
            out.append(r.model_copy(update={"language": guess}))
        else:
            out.append(r)
    return out
