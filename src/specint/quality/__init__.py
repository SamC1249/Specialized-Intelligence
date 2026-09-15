from specint.quality.dedup import DedupReport, deduplicate
from specint.quality.metrics import (
    DEFAULT_PROFILE,
    SCORING_PROFILES,
    WEIGHTS,
    score_record,
    score_records,
)

__all__ = [
    "DEFAULT_PROFILE",
    "SCORING_PROFILES",
    "WEIGHTS",
    "DedupReport",
    "deduplicate",
    "score_record",
    "score_records",
]
