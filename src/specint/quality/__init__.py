from specint.quality.dedup import (
    LICENSE_RANK,
    Fingerprint,
    dedupe,
    dedupe_stats,
    default_fingerprint,
    normalise_title,
)
from specint.quality.metrics import WEIGHTS, score_record, score_records

__all__ = [
    "LICENSE_RANK",
    "WEIGHTS",
    "Fingerprint",
    "dedupe",
    "dedupe_stats",
    "default_fingerprint",
    "normalise_title",
    "score_record",
    "score_records",
]
