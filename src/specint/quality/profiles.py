"""Named quality-scoring profiles.

The `baseline` profile is **byte-identical** to the scorer that produced
`reports/baseline-2026-06-20.json`. Keeping it frozen guarantees that
the June baseline numbers remain reproducible forever, so every new
profile (e.g. `v2`) can be benchmarked against it on the same fixtures
instead of against a moving target.

Add a profile:
  1. Implement new scoring components as pure `(VideoRecord) -> float`
     functions returning values in [0, 1].
  2. Register them in a new `QualityProfile` with weights that sum to 1
     (they will be renormalized if they don't).
  3. Add the profile to `PROFILES`.
  4. Add a test asserting the profile beats the previous one on the
     shared fixtures (comparison-first rule in AGENTS.md).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from specint.quality import metrics as base
from specint.quality.i18n import cooking_relevance
from specint.records import VideoRecord

Scorer = Callable[[VideoRecord], float]


@dataclass(frozen=True)
class QualityProfile:
    """A named mixture of metadata-only scoring components.

    `components` maps a human-readable name to a scorer returning a value
    in [0, 1]. `weights` maps the same keys to non-negative floats; the
    final score is a weighted mean, normalized by `sum(weights)`.
    """

    name: str
    components: dict[str, Scorer] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)

    def score(self, record: VideoRecord) -> float:
        total_w = sum(self.weights.get(k, 0.0) for k in self.components)
        if total_w <= 0:
            return 0.0
        raw = sum(self.weights.get(k, 0.0) * fn(record) for k, fn in self.components.items())
        return raw / total_w

    def score_records(self, records: Iterable[VideoRecord]) -> list[VideoRecord]:
        return [r.with_quality(self.score(r)) for r in records]


def _score_procedural_density(record: VideoRecord) -> float:
    """Reward records that expose step-level supervision.

    0 steps → 0.0, 4+ steps → 1.0, with a linear ramp in between. Four
    steps is the smallest "real recipe" we see in the Common Crawl
    fixture and matches the procedural granularity we want to teach.
    """
    n = len(record.recipe_steps or [])
    if n <= 0:
        return 0.0
    return min(1.0, n / 4.0)


def _score_language_known(record: VideoRecord) -> float:
    """Reward records that expose a usable language tag.

    This is a weak signal, but a declared language is a precondition for
    any downstream multilingual filtering, so we lift it to [0, 1].
    """
    return 1.0 if record.language else 0.0


BASELINE_COMPONENTS: dict[str, Scorer] = {
    "license_clean": base._score_license,
    "duration": base._score_duration,
    "resolution": base._score_resolution,
    "text_density": base._score_text_density,
    "has_steps": base._score_has_steps,
}


BASELINE = QualityProfile(
    name="baseline",
    components=dict(BASELINE_COMPONENTS),
    weights=dict(base.WEIGHTS),
)


V2 = QualityProfile(
    name="v2",
    components={
        **BASELINE_COMPONENTS,
        "cooking_relevance": cooking_relevance,
        "procedural_density": _score_procedural_density,
        "language_known": _score_language_known,
    },
    # v2 is additive over the frozen baseline: all baseline weights are
    # unchanged so the per-record ordering under the baseline components
    # survives, then cooking_relevance pulls cooking-domain records up and
    # procedural_density + language_known are deliberately small to avoid
    # dragging the mean below the baseline on sparse-metadata records.
    weights={
        "license_clean": 0.35,
        "duration": 0.15,
        "resolution": 0.20,
        "text_density": 0.15,
        "has_steps": 0.15,
        "cooking_relevance": 0.30,
        "procedural_density": 0.05,
        "language_known": 0.02,
    },
)


PROFILES: dict[str, QualityProfile] = {
    "baseline": BASELINE,
    "v2": V2,
}


def get_profile(name: str) -> QualityProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"unknown quality profile: {name!r}. known: {sorted(PROFILES)}") from exc
