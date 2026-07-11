"""Cross-source deduplication for VideoRecords.

The comparison harness naively adds ``n_records`` across sources, which
double-counts videos mirrored across services (e.g. a Wikimedia Commons
video also indexed on Internet Archive, or a Common Crawl page that
embeds a PeerTube URL). This module gives us a *metadata-only* signal
of duplication.

Approach (see ``docs/artifacts/2026-07-11-nd-video-dedup.md``):

1. Normalize the title (unicode NFKC, casefold, strip non-alphanumeric),
   compute the trigram set. Two titles are "similar" when their Jaccard
   coefficient is >= ``TITLE_JACCARD_THRESHOLD``.
2. Bucket ``duration_s`` to 2 seconds. If either record has no duration
   we cannot compare durations, so we require the title Jaccard AND
   author-equality to match.
3. Two records match if ``(duration_bucket_equal AND title_similar)``
   OR ``(author_normalized_equal AND title_similar)``.
4. Use union-find to form duplicate groups. The record with the highest
   ``quality_score`` (ties broken by longer duration, then by source
   slug for determinism) is the *winner* for that group.

This is deliberately conservative: we would rather keep two independent
copies than silently drop unique data.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

TITLE_JACCARD_THRESHOLD = 0.6
DURATION_BUCKET_S = 2.0

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", title).casefold()
    return _NON_ALNUM.sub(" ", t).strip()


def _trigrams(text: str) -> set[str]:
    text = _normalize_title(text)
    if len(text) < 3:
        return {text} if text else set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _normalize_author(author: str | None) -> str | None:
    if not author:
        return None
    return unicodedata.normalize("NFKC", author).casefold().strip() or None


def _duration_bucket(seconds: float | None) -> int | None:
    if seconds is None or seconds <= 0:
        return None
    return round(seconds / DURATION_BUCKET_S)


def is_duplicate(a: VideoRecord, b: VideoRecord) -> bool:
    if a.id == b.id:
        return True
    tri_a = _trigrams(a.title)
    tri_b = _trigrams(b.title)
    if _jaccard(tri_a, tri_b) < TITLE_JACCARD_THRESHOLD:
        return False
    bucket_a = _duration_bucket(a.duration_s)
    bucket_b = _duration_bucket(b.duration_s)
    if bucket_a is not None and bucket_b is not None and bucket_a == bucket_b:
        return True
    auth_a = _normalize_author(a.author)
    auth_b = _normalize_author(b.author)
    return bool(auth_a and auth_b and auth_a == auth_b)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def _winner_key(rec: VideoRecord) -> tuple[float, float, str]:
    quality = rec.quality_score if rec.quality_score is not None else 0.0
    duration = rec.duration_s or 0.0
    # Descending priority via negation, then deterministic tie-break.
    return (-quality, -duration, rec.source)


def deduplicate(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return the winner of each duplicate group.

    Runs an O(N^2) pairwise check — fine for the corpora we deal with in
    tests and for per-query rollups. When N gets large we can replace
    the pairwise loop with a title-trigram inverted index.
    """
    items = list(records)
    n = len(items)
    if n <= 1:
        return items

    uf = _UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if is_duplicate(items[i], items[j]):
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    winners: list[VideoRecord] = []
    for members in groups.values():
        group_records = [items[m] for m in members]
        group_records.sort(key=_winner_key)
        winners.append(group_records[0])
    winners.sort(key=lambda r: r.id)
    return winners


def duplicate_rate(records: Iterable[VideoRecord]) -> float:
    items = list(records)
    if not items:
        return 0.0
    unique = deduplicate(items)
    return 1.0 - (len(unique) / len(items))


def unique_duration_s(records: Iterable[VideoRecord]) -> float:
    return float(sum((r.duration_s or 0.0) for r in deduplicate(records)))
