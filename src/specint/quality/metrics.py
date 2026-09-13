"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean      : 1 if license is redistributable, else 0.
  - duration           : peaks at 5 minutes (procedural sweet spot for a
                         single recipe), penalizes very short and very
                         long.
  - resolution         : >=720p ramps from 0 to 1.
  - text_density       : combined length of title + description +
                         recipe_steps.
  - has_steps          : 1 if recipe_steps non-empty (procedural
                         supervision).
  - procedural_density : imperative-verb density from
                         `specint.quality.procedural`.

The default `score_record` weighting is the `baseline` policy from
`specint.quality.policies`; callers may pass any other `QualityPolicy` to
`score_record` / `score_records`. Unknown components in a policy raise a
`KeyError` at scoring time so typos don't silently zero out.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from specint.quality.policies import BASELINE, QualityPolicy
from specint.quality.procedural import procedural_density_score
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


COMPONENTS: dict[str, Callable[[VideoRecord], float]] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": procedural_density_score,
}


# Retained for backward-compat with the 2026-06-20 baseline. New callers
# should read weights off `specint.quality.policies` instead.
WEIGHTS: dict[str, float] = dict(BASELINE.weights)


def score_record(record: VideoRecord, policy: QualityPolicy | None = None) -> float:
    p = policy or BASELINE
    weights = p.weights
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    raw = 0.0
    for name, w in weights.items():
        try:
            fn = COMPONENTS[name]
        except KeyError as exc:
            raise KeyError(
                f"policy {p.name!r} references unknown component {name!r}; "
                f"known={sorted(COMPONENTS)}"
            ) from exc
        raw += w * fn(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    policy: QualityPolicy | None = None,
) -> list[VideoRecord]:
    p = policy or BASELINE
    return [r.with_quality(score_record(r, p)) for r in records]


def component_scores(record: VideoRecord) -> dict[str, float]:
    """Return the raw [0,1] value of every registered component.

    Useful for debugging why a record scored the way it did and for the
    sweep harness's per-component reporting.
    """

    return {name: fn(record) for name, fn in COMPONENTS.items()}
