"""Named quality-weight profiles.

A `Profile` is a dict mapping component name -> weight. Weights must sum
to 1.0. Component functions are registered in `COMPONENTS` and are pure
`VideoRecord -> float in [0, 1]`.

Add a new profile by:
  1. (optionally) registering a new scoring component in `COMPONENTS`,
  2. adding a new entry in `PROFILES` whose weights sum to 1.0,
  3. updating `tests/test_quality.py` with its bounds.

`v1` MUST stay numerically identical to the 2026-06-20 baseline so old
reports remain directly comparable.
"""

from __future__ import annotations

from collections.abc import Callable

from specint.quality.language import detect_language
from specint.quality.relevance import cooking_relevance
from specint.records import VideoRecord

ComponentFn = Callable[[VideoRecord], float]


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


def _score_language_known(record: VideoRecord) -> float:
    if record.language:
        return 1.0
    detected = detect_language((record.title or "") + " " + (record.description or ""))
    return 1.0 if detected else 0.0


COMPONENTS: dict[str, ComponentFn] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "cooking_relevance": cooking_relevance,
    "language_known": _score_language_known,
}

PROFILES: dict[str, dict[str, float]] = {
    "v1": {
        "license_clean": 0.35,
        "duration": 0.15,
        "resolution": 0.20,
        "text_density": 0.15,
        "has_steps": 0.15,
    },
    "v2": {
        "license_clean": 0.30,
        "duration": 0.10,
        "resolution": 0.15,
        "text_density": 0.10,
        "has_steps": 0.10,
        "cooking_relevance": 0.20,
        "language_known": 0.05,
    },
    "v2_cooking": {
        "license_clean": 0.25,
        "duration": 0.10,
        "resolution": 0.10,
        "text_density": 0.05,
        "has_steps": 0.15,
        "cooking_relevance": 0.30,
        "language_known": 0.05,
    },
}


def _validate_profile(profile: str) -> dict[str, float]:
    weights = PROFILES.get(profile)
    if weights is None:
        raise KeyError(f"unknown quality profile: {profile!r} (known: {sorted(PROFILES)})")
    missing = set(weights) - set(COMPONENTS)
    if missing:
        raise KeyError(f"profile {profile!r} references unknown components: {sorted(missing)}")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"profile {profile!r} weights sum to {total:.6f}, expected 1.0")
    return weights


def score_with_profile(record: VideoRecord, profile: str) -> float:
    weights = _validate_profile(profile)
    return sum(w * COMPONENTS[name](record) for name, w in weights.items())


def list_profiles() -> list[str]:
    return sorted(PROFILES)
