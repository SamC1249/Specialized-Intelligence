"""Cross-source deduplication.

A frontier-scale pipeline will inevitably ingest the same video from
multiple sources (e.g. a Wikimedia Commons upload mirrored to the
Internet Archive, or a PeerTube re-upload). Keeping both wastes training
tokens and inflates per-source yield metrics.

Dedup strategy — intentionally conservative:

  Primary key: normalized `media_url` (lower, strip query, strip trailing
      slash). If two records point at the exact same file we merge them.

  Secondary key: a tuple of
      (normalized_title, normalized_author, duration_bucket)
    where duration_bucket rounds duration_s to the nearest 15 s. This
    collapses re-encodes and re-hosts whose durations drift by a few
    seconds (typical for VP9 vs H.264 re-renders) while still separating
    clips that are clearly different cuts.

  Tie-breaker: pick the record with the highest quality_score, falling
  back to license cleanliness, then to the lexicographically-smallest
  source slug for determinism.

This module is pure and offline. The CLI wires it into the comparison
harness so every benchmark row reports how many duplicates it saw.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    folded = unicodedata.normalize("NFKC", value).casefold()
    folded = _PUNCT_RE.sub(" ", folded)
    return _WS_RE.sub(" ", folded).strip()


def _normalize_url(value: str | None) -> str:
    if not value:
        return ""
    s = str(value).strip().lower()
    if "?" in s:
        s = s.split("?", 1)[0]
    if "#" in s:
        s = s.split("#", 1)[0]
    return s.rstrip("/")


def _duration_bucket(seconds: float | None, bucket: float = 15.0) -> int | None:
    if seconds is None or seconds <= 0:
        return None
    return int(round(seconds / bucket))


def _record_sort_key(record: VideoRecord) -> tuple:
    quality = record.quality_score if record.quality_score is not None else -1.0
    return (
        -quality,
        0 if record.license.is_redistributable else 1,
        record.source,
        record.id,
    )


@dataclass(frozen=True)
class DedupeStats:
    n_input: int
    n_output: int
    n_duplicates_dropped: int
    n_cross_source_pairs: int


def dedupe_records(
    records: Iterable[VideoRecord],
) -> tuple[list[VideoRecord], DedupeStats]:
    """Return (deduped records, stats). Order is deterministic by sort key."""
    items = list(records)
    if not items:
        return [], DedupeStats(0, 0, 0, 0)

    groups: dict[tuple, list[VideoRecord]] = {}
    for r in items:
        key = _group_key(r)
        groups.setdefault(key, []).append(r)

    chosen: list[VideoRecord] = []
    cross_source_pairs = 0
    for members in groups.values():
        members.sort(key=_record_sort_key)
        chosen.append(members[0])
        sources = {m.source for m in members}
        if len(members) > 1 and len(sources) > 1:
            cross_source_pairs += 1

    chosen.sort(key=_record_sort_key)
    stats = DedupeStats(
        n_input=len(items),
        n_output=len(chosen),
        n_duplicates_dropped=len(items) - len(chosen),
        n_cross_source_pairs=cross_source_pairs,
    )
    return chosen, stats


def _group_key(record: VideoRecord) -> tuple:
    media_key = _normalize_url(str(record.media_url) if record.media_url else "")
    if media_key:
        return ("media", media_key)
    return (
        "soft",
        _normalize_text(record.title),
        _normalize_text(record.author),
        _duration_bucket(record.duration_s),
    )
