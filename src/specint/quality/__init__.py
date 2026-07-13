from specint.quality.dedup import (
    DedupResult,
    canonical_key,
    deduplicate,
    hamming,
    pairwise_similar,
    simhash,
)
from specint.quality.language import SUPPORTED as SUPPORTED_LANGUAGES
from specint.quality.language import confidence as language_confidence
from specint.quality.language import detect as detect_language
from specint.quality.metrics import (
    WEIGHTS,
    component_scores,
    score_record,
    score_records,
)

__all__ = [
    "SUPPORTED_LANGUAGES",
    "WEIGHTS",
    "DedupResult",
    "canonical_key",
    "component_scores",
    "deduplicate",
    "detect_language",
    "hamming",
    "language_confidence",
    "pairwise_similar",
    "score_record",
    "score_records",
    "simhash",
]
