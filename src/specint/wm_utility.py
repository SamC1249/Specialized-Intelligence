"""World-model utility proxy (Adversarial-Agent plan §7.2).

Real ground-truth ("did including this clip in pretraining lower
next-frame loss on a held-out probe?") requires a training-loop ablation
we do not have today. As a *proxy* we use a metadata- and clip-feature-
only score that correlates with the qualitative arguments in
docs/research/cooking-video-flywheel.md and Summer-22B's pipeline:

  * motion_score in [0, 1]    : optical-flow magnitude proxy — high is good.
  * has_steps in {0, 1}       : procedural supervision present.
  * resolution_factor in [0, 1]
  * duration_factor in [0, 1] : peaks at 5 minutes (procedural sweet spot).
  * static_montage_penalty in [0, 1]: penalises pure plated-food montages
                                       (low motion, beauty-shot keywords).

These weights are an opinion, not a measurement. The intent is to make
the opinion *explicit and overridable* so a future learned filter can
replace it behind the same `score(record) -> float in [0, 1]` interface.

Inputs / outputs:
  * `wm_utility_score(record, motion_score=None) -> float in [0, 1]`
  * `rank_records(records, ...) -> list[VideoRecord]` (highest first)
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.records import VideoRecord

DEFAULT_WEIGHTS: dict[str, float] = {
    "motion": 0.40,
    "has_steps": 0.20,
    "resolution": 0.15,
    "duration": 0.15,
    "anti_montage": 0.10,
}

BEAUTY_SHOT_KEYWORDS = (
    "plated",
    "plating",
    "beauty shot",
    "food porn",
    "asmr",
    "slow motion close-up",
    "macro",
    "still life",
    "stop motion",
)


def _resolution_factor(record: VideoRecord) -> float:
    h = record.height or 0
    if h >= 1080:
        return 1.0
    if h >= 720:
        return 0.75
    if h >= 480:
        return 0.5
    if h > 0:
        return 0.25
    return 0.0


def _duration_factor(record: VideoRecord) -> float:
    d = record.duration_s or 0.0
    if d <= 0:
        return 0.0
    target = 300.0
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))


def _anti_montage_factor(record: VideoRecord, motion_score: float | None) -> float:
    """Returns 1.0 = clearly *not* a static montage, 0.0 = clearly a montage."""
    blob = f"{record.title or ''} {record.description or ''}".lower()
    keyword_hits = sum(1 for k in BEAUTY_SHOT_KEYWORDS if k in blob)
    if motion_score is not None and motion_score < 0.1 and keyword_hits >= 1:
        return 0.0
    if motion_score is not None and motion_score < 0.05:
        return 0.2
    if keyword_hits >= 2:
        return 0.4
    return 1.0


def wm_utility_score(
    record: VideoRecord,
    motion_score: float | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    motion_value = float(motion_score) if motion_score is not None else 0.4
    has_steps_value = 1.0 if record.recipe_steps else 0.0
    resolution_value = _resolution_factor(record)
    duration_value = _duration_factor(record)
    anti_montage = _anti_montage_factor(record, motion_score)

    total_w = sum(w.values()) or 1.0
    score = (
        w["motion"] * motion_value
        + w["has_steps"] * has_steps_value
        + w["resolution"] * resolution_value
        + w["duration"] * duration_value
        + w["anti_montage"] * anti_montage
    )
    return max(0.0, min(1.0, score / total_w))


def rank_records(
    records: Iterable[VideoRecord],
    motion_scores: dict[str, float] | None = None,
) -> list[VideoRecord]:
    """Return records sorted by world-model utility, descending.

    ``motion_scores`` maps record.id -> motion_score in [0, 1]. Missing
    entries fall back to the default in `wm_utility_score`.
    """
    items = list(records)
    keyed = [(wm_utility_score(r, (motion_scores or {}).get(r.id)), r) for r in items]
    keyed.sort(key=lambda kv: (-kv[0], kv[1].id))
    return [r for _, r in keyed]
