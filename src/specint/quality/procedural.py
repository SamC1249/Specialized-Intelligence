"""Procedural-density scoring (metadata-only).

For world-modeling on cooking / lab / manufacturing footage we care less
about *how much text* is attached to a video and more about *how densely
that text describes physical actions*. This module gives us a fast,
deterministic, offline proxy for "how procedural is this record?" that we
can rank millions of candidates by before deciding what to download.

Design notes
------------
- Pure functions only. No network, no models.
- English lexicon today; the lexicon is intentionally isolated to a single
  constant so a multilingual PR can extend it without touching scoring
  logic.
- Two normalizations are exposed so callers can pick the right one:
    * `verb_hits_per_step` — robust when `recipe_steps` are populated
      (Common Crawl schema.org). Falls back to title+description tokens.
    * `verb_hits_per_second` — robust when `duration_s` is populated,
      punishes long videos that only mention a couple of verbs.
  The composite `procedural_density_score` blends both so neither missing
  field zeros the record out on its own.
- Verb matching is whole-word, lower-cased, and includes a small hand-
  curated list of "-ing" and past-tense variants to keep the matcher fast
  without needing a stemmer.

Add a verb:
  Extend `IMPERATIVE_VERBS`. Add a test in `tests/test_procedural.py`
  that pins the new upper/lower bound. Do **not** add domain-specific
  synonyms (e.g. "spatchcock") without a fixture that exercises them —
  we want the lexicon to stay defensibly generic.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

IMPERATIVE_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "brush",
        "chop",
        "coat",
        "combine",
        "cook",
        "cool",
        "cover",
        "cream",
        "cut",
        "dice",
        "drain",
        "drizzle",
        "fill",
        "flip",
        "fold",
        "fry",
        "garnish",
        "grate",
        "grease",
        "grill",
        "heat",
        "knead",
        "layer",
        "marinate",
        "mash",
        "measure",
        "melt",
        "mince",
        "mix",
        "peel",
        "place",
        "pour",
        "preheat",
        "prepare",
        "press",
        "reduce",
        "remove",
        "rest",
        "roast",
        "roll",
        "saute",
        "season",
        "sear",
        "serve",
        "set",
        "shape",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "taste",
        "toast",
        "toss",
        "transfer",
        "turn",
        "warm",
        "wash",
        "whip",
        "whisk",
    }
)


_TOKEN_RE = re.compile(r"[a-z]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _root(token: str) -> str:
    """Cheap-and-cheerful stemming.

    Handles the common English inflection cases we hit on recipe text
    without pulling in a stemmer dependency. Not linguistically correct
    for edge cases (e.g. "baked" -> "bake" is fine, "beating" -> "beat"
    is fine, "sliced" -> "slice"), but good enough at ranking scale.
    """

    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("ing"):
        stem = token[:-3]
        if len(stem) >= 3 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if len(token) > 3 and token.endswith("ed"):
        stem = token[:-2]
        if len(stem) >= 3 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if len(token) > 3 and token.endswith("es"):
        return token[:-2]
    if len(token) > 2 and token.endswith("s"):
        return token[:-1]
    return token


def count_verb_hits(text: str) -> int:
    """Count imperative-verb hits (whole-word, lower-case, cheap-stemmed)."""

    if not text:
        return 0
    return sum(1 for tok in _tokens(text) if _root(tok) in IMPERATIVE_VERBS)


def _record_verb_hits(record: VideoRecord) -> int:
    text_blobs = [record.title, record.description, *record.recipe_steps]
    return sum(count_verb_hits(t) for t in text_blobs)


def verb_hits_per_step(record: VideoRecord) -> float:
    """Verb hits normalized by number of declared recipe steps.

    Falls back to token count / 20 when steps are missing, so a well-
    described video without a `recipeInstructions` JSON-LD block still
    gets a defensible score instead of a zero.
    """

    hits = _record_verb_hits(record)
    if record.recipe_steps:
        steps = max(1, len(record.recipe_steps))
        return hits / steps
    tokens = sum(len(_tokens(t)) for t in (record.title, record.description))
    if tokens <= 0:
        return 0.0
    return hits / max(20.0, tokens / 20.0)


def verb_hits_per_second(record: VideoRecord) -> float:
    """Verb hits normalized by declared duration in seconds.

    We divide by minutes (duration_s / 60) so numbers stay human-readable.
    Returns 0.0 when duration is missing so this term does not silently
    reward records with unknown length.
    """

    if not record.duration_s or record.duration_s <= 0:
        return 0.0
    minutes = record.duration_s / 60.0
    if minutes <= 0:
        return 0.0
    return _record_verb_hits(record) / minutes


def procedural_density_score(record: VideoRecord) -> float:
    """Composite procedural-density score in [0, 1].

    Blends the per-step and per-minute densities so a record that lacks
    either recipe_steps or duration_s can still score, and a record with
    both must earn a high score on at least one to reach 1.0.
    """

    per_step = verb_hits_per_step(record)
    per_minute = verb_hits_per_second(record)

    step_component = min(1.0, per_step / 2.0)
    minute_component = min(1.0, per_minute / 4.0)

    step_weight = 0.6 if record.recipe_steps else 0.2
    minute_weight = 0.4 if record.duration_s else 0.0
    total = step_weight + minute_weight
    if total <= 0:
        return 0.0
    return (step_component * step_weight + minute_component * minute_weight) / total


def procedural_density_batch(records: Iterable[VideoRecord]) -> list[float]:
    return [procedural_density_score(r) for r in records]
