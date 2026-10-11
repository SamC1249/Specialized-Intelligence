from specint.quality.dedupe import DedupeStats, dedupe_records
from specint.quality.language import SEED_TERMS, detect_language, seed_terms
from specint.quality.metrics import score_record, score_records

__all__ = [
    "SEED_TERMS",
    "DedupeStats",
    "dedupe_records",
    "detect_language",
    "score_record",
    "score_records",
    "seed_terms",
]
