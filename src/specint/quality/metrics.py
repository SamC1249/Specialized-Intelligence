"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, normalised back to [0, 1]. Scoring is deliberately
*metadata-only* so we can rank a backlog of millions of candidates
before deciding which to actually download.

Components:
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot),
                          penalises very short and very long content.
  - resolution          : ramps from 0 (unknown/tiny) to 1 (>=1080p).
  - text_density        : combined character length of
                          title + description + recipe_steps.
  - has_steps           : 1 if `recipe_steps` non-empty.
  - language_confidence : offline trigram detector confidence,
                          length-scaled. See `specint.quality.language`.
  - procedural_density  : number of `recipe_steps` normalised to a
                          target of ~8 steps. Distinct from `has_steps`:
                          this rewards *how many* steps exist.

Rationale for adding language / procedural components (see
`docs/plan-2026-07-13.md`):
  - Multilingual corpora are visible on Commons and PeerTube but a
    metadata-only pipeline needs a language signal *before* download.
  - Step-count is the single feature that distinguishes procedural
    supervision (a recipe video) from B-roll (a Commons cooking clip
    with no instructions).

Weights are now overridable per-call (e.g. by the ablation harness) so
we can quantify sensitivity without mutating module state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from specint.quality.language import confidence as language_confidence
from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.12,
    "resolution": 0.15,
    "text_density": 0.13,
    "has_steps": 0.10,
    "language_confidence": 0.10,
    "procedural_density": 0.10,
}


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


def _score_language(record: VideoRecord) -> float:
    base = 0.7 if record.language else 0.0
    text = f"{record.title} {record.description}".strip()
    detector = language_confidence(text)
    return max(base, detector)


def _score_procedural(record: VideoRecord) -> float:
    n = len(record.recipe_steps)
    if n <= 0:
        return 0.0
    target = 8.0
    if n <= target:
        return n / target
    return max(0.4, 1.0 - (n - target) / (target * 4))


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "language_confidence": _score_language,
    "procedural_density": _score_procedural,
}


def component_scores(record: VideoRecord) -> dict[str, float]:
    return {name: fn(record) for name, fn in _COMPONENTS.items()}


def score_record(
    record: VideoRecord,
    weights: Mapping[str, float] | None = None,
) -> float:
    w = dict(weights) if weights else WEIGHTS
    total_weight = sum(w.get(name, 0.0) for name in _COMPONENTS)
    if total_weight <= 0:
        return 0.0
    raw = sum(w.get(name, 0.0) * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    weights: Mapping[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, weights=weights)) for r in records]
