"""Near-duplicate detection.

See `docs/artifacts/2026-08-mlt-dedup.md` for the guiding paper. This
module contains the *metadata-only* first pass; real perceptual /
embedding dedup will land in a future package.
"""

from specint.dedup.minhash import DedupResult, dedup_records, minhash_signature

__all__ = ["DedupResult", "dedup_records", "minhash_signature"]
