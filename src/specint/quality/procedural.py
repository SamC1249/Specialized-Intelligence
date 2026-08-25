"""Procedural quality signals — pure functions of `VideoRecord` metadata.

These signals target *procedural-ness* of a candidate video: does it look
like a full-take, hands-on recipe (great for world-model training) or a
short highlight reel (weak). Every function returns a float in [0, 1]
(or `None` when the metadata needed to score is absent).

The scoring functions here are intentionally cheap — they never touch
video bytes. They are registered with weight 0.0 in `WEIGHTS`
(baseline) and non-zero in `WEIGHTS_EXPERIMENTAL` so we can A/B them.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from specint.records import VideoRecord

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_WORD_RE = re.compile(r"[a-z]+", re.IGNORECASE)


@lru_cache(maxsize=1)
def load_cooking_verbs(path: Path | None = None) -> frozenset[str]:
    file = path or (_DATA_DIR / "cooking_verbs_en.txt")
    if not file.exists():
        return frozenset()
    verbs: set[str] = set()
    for raw_line in file.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip().lower()
        if line:
            verbs.add(line)
    return frozenset(verbs)


def score_aspect_ratio(record: VideoRecord) -> float | None:
    """1.0 at 16:9 (~1.78), decays to 0.0 at 9:16 (~0.56)."""
    if record.aspect_ratio is not None:
        ratio = float(record.aspect_ratio)
    elif record.width and record.height:
        ratio = record.width / record.height
    else:
        return None
    if ratio <= 0:
        return None
    target = 16 / 9
    if ratio >= target:
        # Extra-wide (21:9 cinema) is still procedural-friendly, small penalty only.
        return max(0.5, 1.0 - (ratio - target) / target * 0.5)
    if ratio >= 1.0:
        return 0.6 + 0.4 * ((ratio - 1.0) / (target - 1.0))
    # Portrait / vertical. Hard penalty.
    return max(0.0, 0.4 * ratio / 1.0)


def score_audio_present(record: VideoRecord) -> float | None:
    if record.audio_present is True:
        return 1.0
    if record.audio_present is False:
        return 0.0
    return None


def score_cooking_verbs(record: VideoRecord, verbs: frozenset[str] | None = None) -> float:
    """Fraction of a size-normalized text window that consists of cooking verbs.

    We combine title, description, and recipe steps. A record with no
    cookable text at all scores 0. Saturates fast (1.0 at >= 8 verbs) so
    a very long description doesn't dominate.
    """
    vocab = verbs if verbs is not None else load_cooking_verbs()
    if not vocab:
        return 0.0
    haystack = " ".join([record.title, record.description, *record.recipe_steps]).lower()
    if not haystack.strip():
        return 0.0
    tokens = _WORD_RE.findall(haystack)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in vocab)
    if hits == 0:
        return 0.0
    return min(1.0, hits / 8.0)


def score_shot_density_from_metadata(record: VideoRecord) -> float | None:
    """Heuristic for shot-cut density using recipe_steps count.

    True `hasPart`/VTT cue extraction is a follow-up; for now, we use the
    count of parsed `recipe_steps` normalized by declared duration as a
    proxy: 5 steps in a 5-minute video ~= 60s/step ~= long-take
    procedural (high score); 25 steps in a 3-minute clip == commercial
    edit (low score). Returns None when either signal is absent so the
    aggregator can weight it away instead of penalising missing data.
    """
    if not record.recipe_steps or not record.duration_s or record.duration_s <= 0:
        return None
    seconds_per_step = record.duration_s / max(1, len(record.recipe_steps))
    target = 60.0
    if seconds_per_step >= target:
        return max(0.4, 1.0 - (seconds_per_step - target) / (target * 30))
    return max(0.0, seconds_per_step / target)


PROCEDURAL_COMPONENTS = {
    "aspect_ratio": score_aspect_ratio,
    "audio_present": score_audio_present,
    "cooking_verbs": score_cooking_verbs,
    "shot_density": score_shot_density_from_metadata,
}
