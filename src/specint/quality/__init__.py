"""Quality scoring.

Two scorers are shipped:

  - `v1` (default): the original baseline scorer. See `metrics.py`.
  - `v2`         : adds procedural-density + language-signal components,
                   tuned for step-by-step demonstration video (cooking,
                   surgery, lab work). See `metrics_v2.py`.

Callers should select scorers via `SCORERS[name]` and never import the
underlying `_score_*` helpers directly.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from specint.quality.metrics import score_record, score_records
from specint.quality.metrics_v2 import (
    WEIGHTS_V2,
    component_breakdown,
    score_record_v2,
    score_records_v2,
)
from specint.records import VideoRecord

ScorerFn = Callable[[VideoRecord], float]
BatchScorerFn = Callable[[Iterable[VideoRecord]], list[VideoRecord]]

SCORERS: dict[str, ScorerFn] = {
    "v1": score_record,
    "v2": score_record_v2,
}

BATCH_SCORERS: dict[str, BatchScorerFn] = {
    "v1": score_records,
    "v2": score_records_v2,
}

__all__ = [
    "BATCH_SCORERS",
    "SCORERS",
    "WEIGHTS_V2",
    "BatchScorerFn",
    "ScorerFn",
    "component_breakdown",
    "score_record",
    "score_record_v2",
    "score_records",
    "score_records_v2",
]
