"""Cross-source dedup.

Problem: the same cooking clip can appear on Wikimedia Commons, Internet
Archive, and a PeerTube mirror simultaneously, which inflates `__total__`
and biases diversity metrics.

Approach (metadata-only, deterministic):
  - Fingerprint = `(ascii-folded title slug, duration bucket)`.
  - `duration bucket` = integer `round(duration_s / 5)`; records with
    `None` duration go into a dedicated `-1` bucket.
  - Per fingerprint, keep the record with the *highest quality_score*;
    ties broken by preferring a redistributable license over `UNKNOWN`,
    then by source slug (alphabetical) for determinism.

This is a Phase-1 exact-ish dedup. A future PR will add a perceptual
hash on a sampled thumbnail to catch re-cuts and transcodes.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", normalized.lower()).strip("-")


def _duration_bucket(duration_s: float | None) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return round(duration_s / 5.0)


def fingerprint(record: VideoRecord) -> tuple[str, int]:
    return (_slugify(record.title or ""), _duration_bucket(record.duration_s))


def _rank_key(record: VideoRecord) -> tuple[float, int, int]:
    q = record.quality_score or 0.0
    license_rank = 1 if record.license.is_redistributable else 0
    source_tiebreak = -ord(record.source[0]) if record.source else 0
    return (q, license_rank, source_tiebreak)


@dataclass(frozen=True)
class DedupStats:
    input_count: int
    output_count: int
    duplicate_groups: int

    @property
    def rate(self) -> float:
        if self.input_count == 0:
            return 0.0
        return 1.0 - (self.output_count / self.input_count)


def dedup(records: Iterable[VideoRecord]) -> tuple[list[VideoRecord], DedupStats]:
    """Collapse by fingerprint. Returns (kept, stats)."""
    kept: dict[tuple[str, int], VideoRecord] = {}
    seen = 0
    for record in records:
        seen += 1
        fp = fingerprint(record)
        if fp == ("", -1):
            # Empty title + unknown duration — cannot dedup; pass through
            # with a unique synthetic key.
            kept[(record.id, -1)] = record
            continue
        existing = kept.get(fp)
        if existing is None or _rank_key(record) > _rank_key(existing):
            kept[fp] = record
    output = list(kept.values())
    groups = seen - len(output)
    return output, DedupStats(
        input_count=seen,
        output_count=len(output),
        duplicate_groups=groups,
    )
