"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot for a
                          single recipe), penalizes very short & very
                          long clips.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description + steps.
  - has_steps           : 1 if recipe_steps non-empty (procedural
                          supervision).
  - procedural_density  : cooking-imperative-verb rate across title +
                          description + steps, plus a small bonus for
                          step count. Motivated by H3 in
                          `docs/plan-2026-09-15.md`.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS` (and consider adjusting the named profiles in
     `SCORING_PROFILES`).
  3. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.

Named profiles let us run first-class ablations without editing this
file: `run_comparison(..., profile="license_first")` will re-weight all
records under that vector before aggregating.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.quality.lexicon import COOKING_IMPERATIVE_VERBS
from specint.records import VideoRecord

SCORING_PROFILES: dict[str, dict[str, float]] = {
    "balanced": {
        "license_clean": 0.30,
        "duration": 0.15,
        "resolution": 0.15,
        "text_density": 0.10,
        "has_steps": 0.10,
        "procedural_density": 0.20,
    },
    "license_first": {
        "license_clean": 0.55,
        "duration": 0.10,
        "resolution": 0.10,
        "text_density": 0.05,
        "has_steps": 0.05,
        "procedural_density": 0.15,
    },
    "procedural_first": {
        "license_clean": 0.20,
        "duration": 0.10,
        "resolution": 0.05,
        "text_density": 0.10,
        "has_steps": 0.15,
        "procedural_density": 0.40,
    },
}

DEFAULT_PROFILE = "balanced"

# Backwards-compat alias for the pre-ablation weight vector.
WEIGHTS: dict[str, float] = dict(SCORING_PROFILES[DEFAULT_PROFILE])


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0  # 5 minutes
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))  # decays out to ~1 hour


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


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _score_procedural_density(record: VideoRecord) -> float:
    corpus_parts = [record.title, record.description, *record.recipe_steps]
    toks = _tokens(" ".join(corpus_parts))
    if not toks:
        return 0.0
    verb_hits = sum(1 for t in toks if t in COOKING_IMPERATIVE_VERBS)
    verb_rate = verb_hits / len(toks)
    # Saturate at ~10% verb rate — anything higher is almost certainly a
    # recipe walkthrough. Keep everything in [0, 1].
    verb_component = min(1.0, verb_rate * 10.0)
    step_bonus = min(1.0, len(record.recipe_steps) / 10.0)
    # Weight verb-rate 0.7 vs step count 0.3 so we don't reward blank
    # steps stuffed with fluff.
    return 0.7 * verb_component + 0.3 * step_bonus


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
}


def _resolve_profile(profile: str | dict[str, float] | None) -> dict[str, float]:
    if profile is None:
        return WEIGHTS
    if isinstance(profile, dict):
        return profile
    if profile not in SCORING_PROFILES:
        raise KeyError(f"unknown scoring profile {profile!r}; known: {sorted(SCORING_PROFILES)}")
    return SCORING_PROFILES[profile]


def score_record(record: VideoRecord, profile: str | dict[str, float] | None = None) -> float:
    weights = _resolve_profile(profile)
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    raw = 0.0
    for name, fn in _COMPONENTS.items():
        w = weights.get(name, 0.0)
        if w:
            raw += w * fn(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    profile: str | dict[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, profile=profile)) for r in records]
