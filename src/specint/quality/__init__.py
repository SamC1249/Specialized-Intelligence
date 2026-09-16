from specint.quality.dedup import DedupResult, dedup_key, deduplicate
from specint.quality.metrics import score_record, score_records
from specint.quality.profiles import PROFILES, get_profile
from specint.quality.relevance import (
    COOKING_KEYWORDS,
    RelevanceResult,
    is_cooking_relevant,
    score_relevance,
)

__all__ = [
    "COOKING_KEYWORDS",
    "PROFILES",
    "DedupResult",
    "RelevanceResult",
    "dedup_key",
    "deduplicate",
    "get_profile",
    "is_cooking_relevant",
    "score_record",
    "score_records",
    "score_relevance",
]
