"""Cross-source, metadata-only deduplication.

We do not touch bytes here. Given a stream of `VideoRecord`, we compute a
canonical digest from `(title, duration_bucket, author)` and collapse
records whose digest collides. The dedup key is deliberately conservative:

- Same source + same `source_native_id` -> the record is definitionally the
  same; we always dedup.
- Same `(title_norm, duration_bucket, author_norm)` across sources -> we
  collapse into a single winner, preferring the record with the highest
  `quality_score` (ties broken by source-slug alphabetical order so results
  are deterministic).

Rationale is documented in `docs/plan-2026-08-13.md` (H3). This module is
intentionally pure (no I/O) and stateless, which makes it trivial to unit
test and to reason about in the comparison harness.

Adding a stronger dedup signal (frame-level pHash) is future work — see
`docs/artifacts/2026-08-13-phash-bktree.md` and
`docs/artifacts/2026-08-13-mlt-dedup.md`.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

DURATION_BUCKET_SECONDS = 30
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(value: str | None) -> str:
    """Case-fold, strip diacritics, collapse whitespace, drop punctuation.

    Empty / None input maps to "". Deterministic and pure.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = ascii_only.casefold()
    lowered = _PUNCT_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", lowered).strip()


def duration_bucket(duration_s: float | None, bucket: int = DURATION_BUCKET_SECONDS) -> int:
    """Bucket a duration to the nearest `bucket` seconds; None -> -1 sentinel.

    Bucketing is symmetric around zero so `None` and `0` do NOT collide.
    Positive-but-tiny durations bucket to 1 (never 0), so `None` and a real
    duration cannot share a digest key.
    """
    if duration_s is None or duration_s <= 0:
        return -1
    return max(1, round(float(duration_s) / max(1, bucket)))


def metadata_digest(record: VideoRecord) -> str:
    """Return a stable hex digest for `(title, duration_bucket, author)`."""
    key = "|".join(
        [
            normalize_text(record.title),
            str(duration_bucket(record.duration_s)),
            normalize_text(record.author),
        ]
    )
    return hashlib.blake2b(key.encode("utf-8"), digest_size=16).hexdigest()


def _quality(record: VideoRecord) -> float:
    return record.quality_score if record.quality_score is not None else 0.0


def _tiebreak(record: VideoRecord) -> tuple[float, str, str]:
    return (_quality(record), record.source, record.id)


def dedup_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Collapse duplicates by `(source, source_native_id)` then by digest.

    Winner selection: highest `quality_score`, then source slug alphabetical,
    then `id` alphabetical. Deterministic across runs.

    Empty-title / empty-author / unknown-duration records fall back to their
    unique `id` — we never accidentally merge two records with no signal.
    """
    by_native: dict[tuple[str, str], VideoRecord] = {}
    for r in records:
        key = (r.source, r.source_native_id)
        cur = by_native.get(key)
        if cur is None or _tiebreak(r) > _tiebreak(cur):
            by_native[key] = r

    by_digest: dict[str, VideoRecord] = {}
    for r in by_native.values():
        digest = metadata_digest(r)
        title_norm = normalize_text(r.title)
        author_norm = normalize_text(r.author)
        if not title_norm or duration_bucket(r.duration_s) < 0 or not author_norm:
            digest = f"noop:{r.id}"
        cur = by_digest.get(digest)
        if cur is None or _tiebreak(r) > _tiebreak(cur):
            by_digest[digest] = r

    return sorted(by_digest.values(), key=lambda r: (r.source, r.id))
