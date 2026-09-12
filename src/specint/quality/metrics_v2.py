"""Scorer v2 — extends the v1 metadata-only heuristic with two new signals
that specifically target *procedural* video content (cooking, surgery, lab
work, manufacturing) rather than lecture / talking-head content.

Components added on top of v1:

  - procedural_density : counts imperative cooking-style verb hits in
                         (title + description + recipe_steps) normalised
                         by text length. Discriminates step-by-step
                         demonstration videos from vlogs/reviews.
  - language_signal    : rewards records that declare a language and
                         carry enough text to be usable for language-
                         grounded world modelling.

The v1 components (`license_clean`, `duration`, `resolution`,
`text_density`, `has_steps`) are re-used from `metrics.py` so the two
scorers stay comparable and any regression in a shared component shows
up in *both* reports.

Weights are chosen so `procedural_density` + `has_steps` together
dominate the "is this a demonstration?" axis while license + resolution
still gate download decisions. Weights sum to 1.0 exactly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.quality.metrics import (
    _score_duration,
    _score_has_steps,
    _score_license,
    _score_resolution,
    _score_text_density,
)
from specint.records import VideoRecord

WEIGHTS_V2: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.10,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_density": 0.15,
    "language_signal": 0.10,
}

PROCEDURAL_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "chill",
        "chop",
        "combine",
        "cook",
        "cover",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "drizzle",
        "flip",
        "fold",
        "fry",
        "garnish",
        "grate",
        "grill",
        "heat",
        "juice",
        "knead",
        "layer",
        "marinate",
        "mash",
        "melt",
        "mince",
        "mix",
        "peel",
        "poach",
        "pour",
        "preheat",
        "puree",
        "reduce",
        "rest",
        "roast",
        "roll",
        "saute",
        "sauté",
        "sear",
        "season",
        "serve",
        "shred",
        "sift",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "taste",
        "toast",
        "toss",
        "warm",
        "whip",
        "whisk",
        "zest",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ']+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _text_for_procedural(record: VideoRecord) -> str:
    parts = [record.title or "", record.description or ""]
    parts.extend(record.recipe_steps or [])
    return "\n".join(parts)


def _score_procedural_density(record: VideoRecord) -> float:
    text = _text_for_procedural(record)
    if not text.strip():
        return 0.0
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in PROCEDURAL_VERBS)
    if hits == 0:
        return 0.0
    denom = max(20, len(tokens))
    ratio = hits / denom
    return min(1.0, ratio * 8.0)


def _score_language_signal(record: VideoRecord) -> float:
    text_len = len(record.title or "") + len(record.description or "")
    text_len += sum(len(s) for s in (record.recipe_steps or []))
    if text_len < 20:
        return 0.0
    if record.language:
        return 1.0
    return 0.55


_COMPONENTS_V2 = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
    "language_signal": _score_language_signal,
}


def score_record_v2(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS_V2.values())
    raw = sum(WEIGHTS_V2[name] * fn(record) for name, fn in _COMPONENTS_V2.items())
    return raw / total_weight if total_weight else 0.0


def score_records_v2(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record_v2(r)) for r in records]


def component_breakdown(record: VideoRecord) -> dict[str, float]:
    """Debug helper: returns each raw component in [0,1] plus the final score."""
    parts = {name: fn(record) for name, fn in _COMPONENTS_V2.items()}
    parts["__final__"] = score_record_v2(record)
    return parts
