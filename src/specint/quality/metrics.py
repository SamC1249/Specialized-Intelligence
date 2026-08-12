"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot for
                          a single recipe), penalizes very short and
                          very long.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description +
                          recipe_steps.
  - procedural_density  : count of imperative-verb starts across
                          title + description + recipe_steps, normalized.
                          Motivated by procedural world-model training —
                          more explicit steps = denser action supervision.
  - language_match      : 1 if we can detect a language and it matches
                          `SourceQuery.language` (or the query has no
                          language filter); 0 when we can detect a
                          different one; 0.5 when we cannot detect.

Scoring is done through `score_records(records, query=None)`; `query`
is optional to preserve backward compatibility with the seed baseline.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.quality.language import detect_language
from specint.records import SourceQuery, VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.10,
    "resolution": 0.15,
    "text_density": 0.10,
    "procedural_density": 0.20,
    "language_match": 0.15,
}

# A deliberately small, high-precision English cooking-imperative list.
# Extending this to other languages is future work (see plan-2026-08-12.md
# H4/H5). The regex requires a token boundary so "boil" matches but
# "boiler" does not.
_IMPERATIVES = (
    "add",
    "bake",
    "beat",
    "blend",
    "boil",
    "braise",
    "broil",
    "brown",
    "chop",
    "combine",
    "cool",
    "cover",
    "cut",
    "dice",
    "drain",
    "drizzle",
    "flip",
    "fold",
    "fry",
    "grate",
    "grill",
    "heat",
    "knead",
    "layer",
    "marinate",
    "melt",
    "mince",
    "mix",
    "peel",
    "place",
    "pour",
    "preheat",
    "reduce",
    "remove",
    "roast",
    "roll",
    "saute",
    "sauté",
    "season",
    "sear",
    "serve",
    "simmer",
    "slice",
    "sprinkle",
    "steam",
    "stir",
    "strain",
    "toss",
    "transfer",
    "whip",
    "whisk",
)
_IMPERATIVE_RE = re.compile(
    r"(?<![\w'])(" + "|".join(re.escape(w) for w in _IMPERATIVES) + r")(?![\w'])",
    re.IGNORECASE,
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


def _score_procedural_density(record: VideoRecord) -> float:
    text = " ".join([record.title, record.description, *record.recipe_steps])
    hits = len(_IMPERATIVE_RE.findall(text))
    steps = len(record.recipe_steps)
    target = 8.0
    combined = hits + steps
    return min(1.0, combined / target)


def _score_language_match(record: VideoRecord, query: SourceQuery | None) -> float:
    detected = record.language or detect_language(" ".join([record.title, record.description]))
    wanted = query.language if query else None
    if not wanted:
        return 1.0 if detected else 0.5
    if not detected:
        return 0.5
    return 1.0 if detected.lower().startswith(wanted.lower()) else 0.0


def score_record(record: VideoRecord, query: SourceQuery | None = None) -> float:
    components = {
        "license_clean": _score_license(record),
        "duration": _score_duration(record),
        "resolution": _score_resolution(record),
        "text_density": _score_text_density(record),
        "procedural_density": _score_procedural_density(record),
        "language_match": _score_language_match(record, query),
    }
    total_weight = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[name] * components[name] for name in WEIGHTS)
    return raw / total_weight if total_weight else 0.0


def score_records(
    records: Iterable[VideoRecord],
    query: SourceQuery | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, query)) for r in records]
