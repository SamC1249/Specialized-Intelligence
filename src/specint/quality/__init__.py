from specint.quality.dedup import DedupCluster, dedup_records, duration_bucket, normalize_title
from specint.quality.metrics import (
    WEIGHT_PROFILES,
    WEIGHTS,
    available_profiles,
    detect_language,
    score_record,
    score_records,
)

__all__ = [
    "WEIGHTS",
    "WEIGHT_PROFILES",
    "DedupCluster",
    "available_profiles",
    "dedup_records",
    "detect_language",
    "duration_bucket",
    "normalize_title",
    "score_record",
    "score_records",
]
