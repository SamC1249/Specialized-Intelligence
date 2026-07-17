"""Cross-source duplicate detection.

The problem: hobbyist chefs cross-post the same recipe video on multiple
open-web hosts (Wikimedia Commons + Internet Archive is a common
pattern; the same PeerTube video is also often mirrored across
federated instances). Without deduplication our "internet-scale" counts
double-count identical content and skew license-cleanliness ratios.

Approach — cheap, deterministic, and offline-testable:

  1. Normalise the title (Unicode NFKC, casefold, strip punctuation,
     collapse whitespace).
  2. Bucket the duration to the nearest 10 seconds. `None` durations
     do not collide with a known-duration record.
  3. Compute an author key (casefold + strip whitespace, or empty).
  4. Group records that share the tuple `(title_norm, dur_bucket,
     author_key)`. If the author key is empty, we still allow the
     merge — many upstreams don't carry author metadata.

We deliberately do NOT do fuzzy string distance today; that class of
signal is easy to add but hard to test deterministically. This module
returns *groups*: each group is a list of `VideoRecord` that we
believe are duplicates. The caller decides which one to keep (a
convenience `pick_canonical` prefers the record with the highest
`quality_score`, falling back to license cleanliness, then source-slug
alphabetically for determinism).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    if not title:
        return ""
    nk = unicodedata.normalize("NFKC", title)
    nk = _PUNCT_RE.sub(" ", nk).casefold()
    return _WS_RE.sub(" ", nk).strip()


def _duration_bucket(seconds: float | None, bucket: int = 10) -> int | None:
    if seconds is None or seconds <= 0:
        return None
    return round(seconds / bucket)


def _author_key(author: str | None) -> str:
    if not author:
        return ""
    return _WS_RE.sub(" ", author.strip()).casefold()


def _dedup_key(record: VideoRecord) -> tuple[str, int | None, str]:
    return (
        normalize_title(record.title),
        _duration_bucket(record.duration_s),
        _author_key(record.author),
    )


def group_duplicates(records: Iterable[VideoRecord]) -> list[list[VideoRecord]]:
    """Group records by our dedup key. Deterministic ordering.

    Groups are sorted by (title_norm, source, source_native_id) so the
    output is stable across runs. Records with an empty normalized
    title are treated as unique (never merged) — we refuse to merge on
    a fully-empty key.
    """
    buckets: dict[tuple[str, int | None, str], list[VideoRecord]] = {}
    unmergeable: list[list[VideoRecord]] = []
    for r in records:
        key = _dedup_key(r)
        if not key[0]:
            unmergeable.append([r])
            continue
        buckets.setdefault(key, []).append(r)

    def _rec_sort(r: VideoRecord) -> tuple[str, str]:
        return (r.source, r.source_native_id)

    groups: list[list[VideoRecord]] = []
    for key in sorted(buckets):
        group = sorted(buckets[key], key=_rec_sort)
        groups.append(group)
    groups.extend(unmergeable)
    return groups


def pick_canonical(group: list[VideoRecord]) -> VideoRecord:
    """Choose the best representative of a duplicate group.

    Preference order:
      1. Highest `quality_score` (None treated as -inf).
      2. License-clean first.
      3. Source slug alphabetically (deterministic tiebreak).
    """
    if not group:
        raise ValueError("cannot pick canonical from empty group")

    def _rank(r: VideoRecord) -> tuple[float, int, str]:
        q = r.quality_score if r.quality_score is not None else float("-inf")
        clean = 1 if r.license.is_redistributable else 0
        return (-q, -clean, r.source)

    return sorted(group, key=_rank)[0]


def deduplicate(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return one canonical record per duplicate group."""
    return [pick_canonical(g) for g in group_duplicates(records)]
