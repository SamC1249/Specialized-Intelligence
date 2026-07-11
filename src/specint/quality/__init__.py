"""Quality scoring package.

Two scorers coexist so we can measure improvements instead of asserting
them:

- ``v1`` (``metrics``): the seed scorer that established the baseline
  in ``reports/baseline-2026-06-20.json``.
- ``v2`` (``metrics_v2``): adversarial improvements. See
  ``docs/plan-2026-07-11.md`` for the hypotheses and success criteria.

Import ``score_record``/``score_records`` from either module — or use
``get_scorer('v1'|'v2')`` for dispatch.
"""

from collections.abc import Callable

from specint.quality import metrics, metrics_v2
from specint.quality.metrics import score_record, score_records
from specint.records import VideoRecord

Scorer = Callable[[VideoRecord], float]

SCORERS: dict[str, Scorer] = {
    "v1": metrics.score_record,
    "v2": metrics_v2.score_record,
}


def get_scorer(version: str) -> Scorer:
    try:
        return SCORERS[version]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"unknown scorer version {version!r}, expected one of {list(SCORERS)}"
        ) from exc


__all__ = [
    "SCORERS",
    "Scorer",
    "get_scorer",
    "metrics",
    "metrics_v2",
    "score_record",
    "score_records",
]
