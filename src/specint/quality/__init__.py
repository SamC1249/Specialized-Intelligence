from specint.quality.dedup import DedupReport, canonicalize_url, dedupe, jaccard
from specint.quality.langdetect import backfill_languages, detect
from specint.quality.metrics import score_record, score_records
from specint.quality.procedural import (
    PROFILES,
    score_procedural_density,
    score_record_v2,
    score_records_with_profile,
)

__all__ = [
    "PROFILES",
    "DedupReport",
    "backfill_languages",
    "canonicalize_url",
    "dedupe",
    "detect",
    "jaccard",
    "score_procedural_density",
    "score_record",
    "score_record_v2",
    "score_records",
    "score_records_with_profile",
]
