"""Quality scorer v2 — additive metadata-only refinements over v1.

Motivation (see `docs/plan-2026-07-14.md`, H2):

v1 rewards structured recipe pages (has_steps=1) but is blind to rich
prose narration in a video *description*. It also ignores language,
which means a Bosnian or Hindi Wikimedia clip scores the same as an
English clip even though our current cooking corpus is English-first.

v2 adds two components, both metadata-only and both in [0, 1]:

- `procedural`      : density of English cooking-verb tokens per 100
                      words across (title + description + recipe_steps).
                      A single occurrence is worth partial credit; the
                      curve saturates at ~1 verb per 30 words which
                      matches YouTube instructional narration.
- `english_signal`  : share of tokens in the top-50 English stopword
                      list. Language declared on the record is honored:
                      if `record.language` explicitly starts with `en`,
                      we short-circuit to 1.0. If it is non-English,
                      the stopword ratio is halved (soft penalty).

Weights are tuned so that v2's total remains in [0, 1] and does *not*
depend on English-signal alone (max English contribution is 0.10).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

WEIGHTS_V2: dict[str, float] = {
    "license_clean": 0.32,
    "duration": 0.13,
    "resolution": 0.18,
    "text_density": 0.10,
    "has_steps": 0.09,
    "procedural": 0.08,
    "english_signal": 0.10,
}

COOKING_VERBS: frozenset[str] = frozenset(
    {
        "bake",
        "beat",
        "blend",
        "boil",
        "broil",
        "brown",
        "chill",
        "chop",
        "combine",
        "cook",
        "cool",
        "cover",
        "cream",
        "cut",
        "dice",
        "drain",
        "drizzle",
        "flip",
        "fold",
        "freeze",
        "fry",
        "garnish",
        "grate",
        "grease",
        "grill",
        "heat",
        "julienne",
        "knead",
        "marinate",
        "melt",
        "mix",
        "peel",
        "poach",
        "pound",
        "pour",
        "preheat",
        "puree",
        "reduce",
        "roast",
        "rub",
        "saute",
        "sauté",
        "sear",
        "season",
        "serve",
        "simmer",
        "slice",
        "steam",
        "stew",
        "stir",
        "strain",
        "temper",
        "toast",
        "toss",
        "whip",
        "whisk",
    }
)

EN_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "not",
        "of",
        "on",
        "or",
        "she",
        "so",
        "that",
        "the",
        "their",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)

_TOKEN_RE = re.compile(r"[a-zA-ZàâçéèêëîïôûùüÿñæœÀÂÇÉÈÊËÎÏÔÛÙÜŸÑÆŒ']+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _corpus(record: VideoRecord) -> str:
    return " ".join(
        [
            record.title or "",
            record.description or "",
            " ".join(record.recipe_steps or []),
        ]
    )


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))


def _score_resolution(record: VideoRecord) -> float:
    h = record.height
    if h is None or h <= 0:
        return 0.0
    if h >= 1080:
        return 1.0
    if h >= 720:
        return 0.8
    if h >= 480:
        return 0.5
    return 0.2


def _score_text_density(record: VideoRecord) -> float:
    chars = len(record.title) + len(record.description)
    chars += sum(len(s) for s in record.recipe_steps)
    if chars <= 0:
        return 0.0
    target = 800.0
    return min(1.0, chars / target)


def _score_has_steps(record: VideoRecord) -> float:
    return 1.0 if record.recipe_steps else 0.0


def _score_procedural(record: VideoRecord) -> float:
    tokens = _tokens(_corpus(record))
    if not tokens:
        return 0.0
    verbs = sum(1 for t in tokens if t in COOKING_VERBS)
    if verbs == 0:
        return 0.0
    density = verbs / max(len(tokens), 1)
    saturation = 1.0 / 30.0
    return min(1.0, density / saturation)


def _score_english_signal(record: VideoRecord) -> float:
    lang = (record.language or "").lower()
    if lang.startswith("en"):
        return 1.0
    tokens = _tokens(_corpus(record))
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in EN_STOPWORDS)
    ratio = hits / len(tokens)
    scaled = min(1.0, ratio / 0.15)
    return scaled * 0.5 if lang and not lang.startswith("en") else scaled


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural": _score_procedural,
    "english_signal": _score_english_signal,
}


def score_record_v2(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS_V2.values())
    raw = sum(WEIGHTS_V2[name] * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight if total_weight else 0.0


def score_records_v2(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record_v2(r)) for r in records]
