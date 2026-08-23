"""Cross-source, metadata-only deduplication.

Same video re-uploaded to Wikimedia Commons, Internet Archive, or a
PeerTube mirror will show up as multiple `VideoRecord` rows. To keep the
aggregate corpus honest, we collapse records that share a normalized
title *and* a rounded duration into a single "representative" record.

This is a **conservative** first cut:
  - Metadata only, no video / audio fingerprinting.
  - Deliberately does not attempt cross-language matching (e.g. an
    English mirror of a Japanese original will NOT be merged).
  - Preference order for the representative row:
      1. license is redistributable (avoid picking a RESTRICTED row).
      2. higher ``quality_score`` (fall back to 0.0 if None).
      3. longer ``duration_s`` (prefer the more complete cut).
      4. earlier ``id`` (deterministic tie-breaker).

The choice is exposed as ``dedup_records`` so the harness can compute a
"pre-dedup vs post-dedup" delta and surface it in `BenchmarkResult`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+", re.UNICODE)
_DURATION_BUCKET_S = 10.0


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    lowered = unicodedata.normalize("NFKC", title).lower()
    no_punct = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", no_punct).strip()


def _bucket_duration(duration_s: float | None) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return round(duration_s / _DURATION_BUCKET_S)


def fingerprint(record: VideoRecord) -> tuple[str, int]:
    return (_normalize_title(record.title), _bucket_duration(record.duration_s))


def _preference_key(record: VideoRecord) -> tuple[int, float, float, str]:
    return (
        1 if record.license.is_redistributable else 0,
        record.quality_score or 0.0,
        record.duration_s or 0.0,
        record.id,
    )


def dedup_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return the deduplicated list, in first-seen order per fingerprint.

    Records with an "empty" fingerprint (blank title AND unknown
    duration) are never merged — we cannot safely conclude they are the
    same. Each such record keeps its own bucket keyed by its ``id``.
    """
    best: dict[object, VideoRecord] = {}
    first_seen: dict[object, int] = {}

    for idx, rec in enumerate(records):
        fp = fingerprint(rec)
        key: object = fp if (fp[0] or fp[1] >= 0) else ("__unmergeable__", rec.id)
        current = best.get(key)
        if current is None:
            best[key] = rec
            first_seen[key] = idx
        elif _preference_key(rec) > _preference_key(current):
            best[key] = rec

    ordered_keys = sorted(best.keys(), key=lambda k: first_seen[k])
    return [best[k] for k in ordered_keys]


def dedup_stats(records: Iterable[VideoRecord]) -> tuple[int, int]:
    """Return ``(n_before, n_after)`` counts."""
    ordered = list(records)
    return len(ordered), len(dedup_records(ordered))
