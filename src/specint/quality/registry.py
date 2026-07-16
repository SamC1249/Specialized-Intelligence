"""Named quality-scorer registry.

Callers pick a scorer by *name* (e.g. `"v1"`, `"v2"`) so benchmark
reports can record which scorer produced the numbers. This is the
foundation of A/B comparison between scorer versions — see
`compare.harness.run_matrix` and `python -m specint compare
--scorer v2`.

Adding a scorer:
  1. Implement `score_record` and `score_records` in a new module.
  2. Register the pair here.
  3. Add the scorer name to the CI comparison matrix so it produces
     a fresh `reports/scorer-compare-YYYY-MM-DD.json` on every run.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from specint.quality import metrics as v1
from specint.quality import v2 as v2_mod
from specint.records import VideoRecord

SingleScorer = Callable[[VideoRecord], float]
BatchScorer = Callable[[Iterable[VideoRecord]], list[VideoRecord]]


_SINGLE: dict[str, SingleScorer] = {
    "v1": v1.score_record,
    "v2": v2_mod.score_record,
}
_BATCH: dict[str, BatchScorer] = {
    "v1": v1.score_records,
    "v2": v2_mod.score_records,
}


def available() -> tuple[str, ...]:
    return tuple(sorted(_SINGLE.keys()))


def get_scorer(name: str) -> SingleScorer:
    try:
        return _SINGLE[name]
    except KeyError as exc:
        raise ValueError(f"unknown scorer {name!r}; available: {available()}") from exc


def get_batch_scorer(name: str) -> BatchScorer:
    try:
        return _BATCH[name]
    except KeyError as exc:
        raise ValueError(f"unknown scorer {name!r}; available: {available()}") from exc


def score_records(records: Iterable[VideoRecord], scorer: str = "v1") -> list[VideoRecord]:
    return get_batch_scorer(scorer)(records)
