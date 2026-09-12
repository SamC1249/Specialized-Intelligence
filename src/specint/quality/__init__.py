from specint.quality.dedup import (
    DedupResult,
    DuplicateGroup,
    aggregate_dedup,
    dedup_by_source,
    dedup_records,
    normalize_url,
    title_tokens,
)
from specint.quality.invariants import (
    InvariantViolation,
    assert_records,
    check_records,
    summarize,
)
from specint.quality.metrics import score_record, score_records

__all__ = [
    "DedupResult",
    "DuplicateGroup",
    "InvariantViolation",
    "aggregate_dedup",
    "assert_records",
    "check_records",
    "dedup_by_source",
    "dedup_records",
    "normalize_url",
    "score_record",
    "score_records",
    "summarize",
    "title_tokens",
]
