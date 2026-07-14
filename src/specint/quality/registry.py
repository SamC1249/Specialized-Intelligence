"""Named registry of scorer callables.

We register scorers by short id so the comparison harness and the CLI
can select them (`--scorer v1` vs `--scorer v2`) without touching the
harness code. This is how we A/B test scoring changes systematically.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from specint.quality.metrics import score_record, score_records
from specint.quality.v2 import score_record_v2, score_records_v2
from specint.records import VideoRecord

RecordScorer = Callable[[VideoRecord], float]
RecordsScorer = Callable[[Iterable[VideoRecord]], list[VideoRecord]]

SCORERS: dict[str, tuple[RecordScorer, RecordsScorer]] = {
    "v1": (score_record, score_records),
    "v2": (score_record_v2, score_records_v2),
}

DEFAULT_SCORER = "v1"


def get_scorer(name: str) -> tuple[RecordScorer, RecordsScorer]:
    if name not in SCORERS:
        raise KeyError(f"unknown scorer {name!r}; known: {sorted(SCORERS)}")
    return SCORERS[name]


def scorer_names() -> list[str]:
    return sorted(SCORERS)
