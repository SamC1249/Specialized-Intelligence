"""Metadata-only near-duplicate detection.

Cheap: no media fetch, no perceptual hashing. We build a stable
`dedup_key` from three metadata signals shown to work well as a first-
pass filter on user-uploaded video:

1. **Normalized title shingles.** We lowercase, NFKC-normalize, strip
   punctuation, collapse whitespace, drop stop-tokens, and take the
   sorted set of 3-grams over the resulting tokens. Two records with
   the same shingle set + one other matching signal are treated as the
   same content.
2. **Duration bucket.** `round(duration_s / 5)` seconds (5-second
   quantization). Cooking videos edited by different uploaders rarely
   land in the same 5s bucket by accident; identical mirrors always do.
3. **Author slug.** Lowercased, alphanumeric-only author name, or the
   empty string when absent. Author is a *positive* signal for dedup
   only when non-empty — different authors of a 5-minute video called
   "Chocolate Cake" are *not* duplicates.

A cluster is any equivalence class under the relation
`(shingles == shingles) AND (duration_bucket == duration_bucket) AND
(author_slug == author_slug OR both empty)`.

The relation is not perfectly transitive in the presence of missing
data, so we use a union-find over records instead of a naive groupby.

This module is the baseline that any future perceptual-hash-based
dedup must beat on the same fixture corpus. See
`docs/artifacts/2026-07-12-perceptual-video-hash-dedup.md`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")

_STOP_TOKENS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "with",
        "how",
        "to",
        "for",
        "in",
        "on",
        "video",
        "recipe",
        "cooking",
        "hd",
        "4k",
        "1080p",
        "720p",
        "part",
    }
)


def _normalize_title(title: str) -> list[str]:
    if not title:
        return []
    nfkc = unicodedata.normalize("NFKC", title).lower()
    no_punct = _PUNCT_RE.sub(" ", nfkc)
    tokens = _WS_RE.sub(" ", no_punct).strip().split(" ")
    return [t for t in tokens if t and t not in _STOP_TOKENS]


def _shingles(tokens: list[str], n: int = 3) -> frozenset[tuple[str, ...]]:
    if not tokens:
        return frozenset()
    if len(tokens) < n:
        return frozenset({tuple(tokens)})
    return frozenset(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _author_slug(author: str | None) -> str:
    if not author:
        return ""
    slug = unicodedata.normalize("NFKC", author).lower()
    return re.sub(r"[^a-z0-9]+", "", slug)


def _duration_bucket(duration_s: float | None) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return round(duration_s / 5.0)


@dataclass(frozen=True)
class DedupKey:
    shingles: frozenset[tuple[str, ...]]
    duration_bucket: int | None
    author_slug: str

    def is_duplicate_of(self, other: DedupKey) -> bool:
        if not self.shingles or not other.shingles:
            return False
        if self.shingles != other.shingles:
            return False
        if self.duration_bucket is None or other.duration_bucket is None:
            duration_ok = True
        else:
            duration_ok = self.duration_bucket == other.duration_bucket
        if not duration_ok:
            return False
        return not (
            self.author_slug and other.author_slug and self.author_slug != other.author_slug
        )


def dedup_key(record: VideoRecord) -> DedupKey:
    return DedupKey(
        shingles=_shingles(_normalize_title(record.title)),
        duration_bucket=_duration_bucket(record.duration_s),
        author_slug=_author_slug(record.author),
    )


@dataclass(frozen=True)
class DedupCluster:
    representative_id: str
    member_ids: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.member_ids)


class _UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def dedup_records(
    records: Iterable[VideoRecord],
) -> tuple[list[VideoRecord], list[DedupCluster]]:
    """Return `(deduped_records, clusters)`.

    `deduped_records` keeps one representative per cluster, chosen as
    the first record in input order (stable). Records with empty
    shingles (untitled, or entirely stop-tokens) are never merged and
    always appear in the deduped output.
    """
    items = list(records)
    if not items:
        return [], []

    keys = [dedup_key(r) for r in items]
    uf = _UnionFind([r.id for r in items])
    for i, ri in enumerate(items):
        if not keys[i].shingles:
            continue
        for j in range(i + 1, len(items)):
            if not keys[j].shingles:
                continue
            if keys[i].is_duplicate_of(keys[j]):
                uf.union(ri.id, items[j].id)

    order = {r.id: idx for idx, r in enumerate(items)}
    groups: dict[str, list[str]] = {}
    for r in items:
        groups.setdefault(uf.find(r.id), []).append(r.id)

    clusters: list[DedupCluster] = []
    representatives: set[str] = set()
    for _root, members in groups.items():
        members_sorted = sorted(members, key=lambda x: order[x])
        rep = members_sorted[0]
        representatives.add(rep)
        clusters.append(DedupCluster(representative_id=rep, member_ids=tuple(members_sorted)))

    deduped = [r for r in items if r.id in representatives]
    clusters.sort(key=lambda c: order[c.representative_id])
    return deduped, clusters


__all__ = [
    "DedupCluster",
    "DedupKey",
    "dedup_key",
    "dedup_records",
]
