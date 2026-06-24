"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean      : ``is_redistributable * license_confidence``.
  - duration           : peaks at 5 minutes (procedural sweet spot).
  - resolution         : >=720p ramps from 0 to 1.
  - text_density       : combined length of title + description + recipe_steps.
  - has_steps          : 1 if recipe_steps non-empty.
  - procedural_density : verb / step / digit cues that the clip shows a
                         procedure rather than a static beauty shot.

Adding a component:
  1. Implement a new ``_score_*`` function returning a float in [0, 1].
  2. Add it to ``WEIGHTS`` with a documented rationale.
  3. Update tests in ``tests/test_quality.py`` with the new bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.10,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_density": 0.25,
}

# Short, language-agnostic-ish list of cooking imperatives. Kept tiny on
# purpose: the heuristic must lose gracefully on non-English text rather
# than rank everything English-first. A learned procedural classifier is
# the planned v1 successor.
IMPERATIVE_VERBS: tuple[str, ...] = (
    "add",
    "bake",
    "blend",
    "boil",
    "chop",
    "combine",
    "cook",
    "cut",
    "drain",
    "flip",
    "fold",
    "fry",
    "grate",
    "grill",
    "heat",
    "knead",
    "marinate",
    "melt",
    "mince",
    "mix",
    "pour",
    "preheat",
    "roast",
    "saute",
    "season",
    "serve",
    "simmer",
    "slice",
    "stir",
    "toast",
    "whisk",
)
_VERB_RE = re.compile(
    r"\b(" + "|".join(IMPERATIVE_VERBS) + r")\b",
    flags=re.IGNORECASE,
)
_STEP_MARKER_RE = re.compile(r"\b(?:step\s*\d+|\d+\s*[\.\)])", flags=re.IGNORECASE)


def _score_license(record: VideoRecord) -> float:
    if not record.license.is_redistributable:
        return 0.0
    return max(0.0, min(1.0, record.license_confidence))


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0  # 5 minutes
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


def _score_procedural_density(record: VideoRecord) -> float:
    text_for_verbs = " ".join([record.title, record.description, " ".join(record.recipe_steps)])
    verbs = len(_VERB_RE.findall(text_for_verbs))
    step_marker = 1.0 if _STEP_MARKER_RE.search(text_for_verbs) else 0.0
    steps_component = min(1.0, len(record.recipe_steps) / 6.0)
    verbs_component = min(1.0, verbs / 5.0)
    return 0.5 * steps_component + 0.3 * verbs_component + 0.2 * step_marker


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
}


def component_scores(record: VideoRecord) -> dict[str, float]:
    """Return per-component scores in [0, 1] for ``record``. Pure."""
    return {name: float(fn(record)) for name, fn in _COMPONENTS.items()}


def score_record(record: VideoRecord, weights: dict[str, float] | None = None) -> float:
    """Weighted sum of ``component_scores(record)`` in [0, 1].

    ``weights`` overrides the module-level ``WEIGHTS`` and is normalised by
    its own sum so the result remains in [0, 1] even when a caller zeros
    out some components (used by ``compare.ablation``).
    """
    w = weights or WEIGHTS
    total_weight = sum(max(0.0, v) for v in w.values())
    if total_weight <= 0:
        return 0.0
    components = component_scores(record)
    raw = sum(max(0.0, w.get(name, 0.0)) * components[name] for name in _COMPONENTS)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    weights: dict[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, weights=weights)) for r in records]
