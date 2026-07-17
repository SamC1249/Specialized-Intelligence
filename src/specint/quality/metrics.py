"""Metadata-only quality scoring.

Every component returns a float in [0, 1]. The final score is a
weighted mean (weights renormalised so the score always stays in
[0, 1] regardless of which components a caller enables). Scoring is
deliberately metadata-only so we can rank millions of candidates
before deciding which to actually fetch.

Components (2026-07-17):
  - license_clean     : 1 if license is redistributable, else 0.
  - duration          : peaks at 5 min (procedural sweet spot),
                        decays out to ~1 hour.
  - resolution        : ramps from 0 at <480p to 1.0 at >=1080p.
  - text_density      : combined length of title + description +
                        recipe_steps, normalised to 800 chars.
  - has_steps         : legacy 1/0 boolean (kept for backwards-compat
                        so old baselines remain comparable).
  - procedural_density: # of imperative cooking verbs hit across
                        title + description + steps, normalised to 8.
                        Strictly stronger than `has_steps` — a 15-step
                        recipe scores higher than a 3-step one.
  - cooking_relevance : # of cooking-domain noun hits, normalised to
                        6. Multilingual (see lexicon.py).

Adding a new component:
  1. Implement `_score_x(record) -> float in [0, 1]`.
  2. Register it in `ALL_COMPONENTS`.
  3. Add to a `WeightConfig` (either the default `DEFAULT_WEIGHTS` or
     an ablation config in `compare/ablation.py`).
  4. Add tests documenting the lower/upper bounds.

The old `WEIGHTS` module-level dict is retained as `DEFAULT_WEIGHTS`
so existing callers `from specint.quality.metrics import WEIGHTS`
continue to work.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from specint.quality.lexicon import DEFAULT_LEXICON, Lexicon
from specint.records import VideoRecord


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


def _record_text(record: VideoRecord) -> str:
    return " ".join([record.title, record.description, *record.recipe_steps])


def make_procedural_density(lexicon: Lexicon = DEFAULT_LEXICON) -> Callable[[VideoRecord], float]:
    def _score(record: VideoRecord) -> float:
        verbs = lexicon.verb_hits(_record_text(record))
        steps = len(record.recipe_steps)
        combined = verbs + steps
        if combined <= 0:
            return 0.0
        return min(1.0, combined / 8.0)

    return _score


def make_cooking_relevance(lexicon: Lexicon = DEFAULT_LEXICON) -> Callable[[VideoRecord], float]:
    def _score(record: VideoRecord) -> float:
        nouns = lexicon.noun_hits(_record_text(record))
        kw = sum(1 for k in record.keywords if lexicon.noun_hits(k) or lexicon.verb_hits(k))
        combined = nouns + kw
        if combined <= 0:
            return 0.0
        return min(1.0, combined / 6.0)

    return _score


ALL_COMPONENTS: dict[str, Callable[[VideoRecord], float]] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": make_procedural_density(),
    "cooking_relevance": make_cooking_relevance(),
}


DEFAULT_WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.10,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.05,
    "procedural_density": 0.15,
    "cooking_relevance": 0.15,
}

WEIGHTS = DEFAULT_WEIGHTS


@dataclass(frozen=True)
class WeightConfig:
    name: str
    weights: Mapping[str, float]

    def score(self, record: VideoRecord) -> float:
        return score_record(record, weights=self.weights)


def score_record(record: VideoRecord, weights: Mapping[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    total_weight = sum(w.values())
    if total_weight <= 0:
        return 0.0
    raw = 0.0
    for name, weight in w.items():
        component = ALL_COMPONENTS.get(name)
        if component is None or weight == 0:
            continue
        raw += weight * component(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    weights: Mapping[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, weights=weights)) for r in records]
