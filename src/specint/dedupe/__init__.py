"""Cross-source deduplication utilities (metadata-only)."""

from specint.dedupe.urlhash import (
    canonical_url,
    dedupe_summary,
    jaccard,
    merge_records,
    title_shingles,
)

__all__ = [
    "canonical_url",
    "dedupe_summary",
    "jaccard",
    "merge_records",
    "title_shingles",
]
