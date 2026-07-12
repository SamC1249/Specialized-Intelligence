"""Cross-source, metadata-only deduplication.

We assume the same video may show up in more than one source: e.g. a
Wikimedia Commons `.webm` embedded in a Common Crawl recipe page, or an
Internet Archive mirror of a PeerTube upload. Metadata-only dedup is
enough to catch the obvious cases and *must* run before we quote
"unique hours of CC video" numbers to anyone.

Signals used, in this order:

1. **Canonical URL** — two records with the same `str(record.url)`
   after protocol/case normalisation belong to the same group.
2. **Media URL** — same as above for `record.media_url`.
3. **Title-shingle Jaccard + duration bucket** — for the same
   duration bucket (60 s wide up to 10 min, then 5 min buckets
   thereafter), records with word-shingled title Jaccard ≥ 0.8 are
   merged. This is deliberately conservative: identical titles alone
   are not enough (too many "Pasta" collisions), and duration bucket
   alone is not enough (too many 5-minute clips).

We never merge across license boundaries. A CC0 record and an
UNKNOWN record with the same URL are almost certainly the same
physical video, but treating them as one would let UNKNOWN records
inherit CC0 media_urls. Instead, when a group spans license classes,
we keep the record with the highest license tier as the "survivor"
and record the other members in `duplicates`.

Determinism: the survivor of a group is the record with (highest
license tier, longest known duration, lexicographically smallest
`id`) — a total order, so re-runs are reproducible.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from specint.records import License, VideoRecord

_WORD_RE = re.compile(r"[a-z0-9]+")

_LICENSE_TIER: dict[License, int] = {
    License.CC0: 6,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}

_TITLE_JACCARD_THRESHOLD = 0.8


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _shingles(tokens: list[str], n: int = 2) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _duration_bucket(seconds: float | None) -> int | None:
    if seconds is None or seconds <= 0:
        return None
    if seconds <= 600:
        return int(seconds // 60)
    return 10 + int((seconds - 600) // 300)


def _normalise_url(url: object) -> str:
    if url is None:
        return ""
    return str(url).strip().lower().rstrip("/")


def _survivor_key(record: VideoRecord) -> tuple[int, float, str]:
    tier = _LICENSE_TIER.get(record.license, 0)
    duration = record.duration_s if record.duration_s is not None else -1.0
    return (-tier, -duration, record.id)


class DedupCounters(NamedTuple):
    n_input: int
    n_output: int
    merged_by_url: int
    merged_by_media_url: int
    merged_by_title: int


class DedupResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[VideoRecord]
    duplicates: dict[str, list[str]] = Field(default_factory=dict)
    counters: dict[str, int] = Field(default_factory=dict)


def dedup_records(records: Iterable[VideoRecord]) -> DedupResult:
    items = list(records)

    by_url: dict[str, int] = {}
    by_media: dict[str, int] = {}

    groups: list[list[int]] = []
    group_of: list[int] = [-1] * len(items)
    merged_by_url = 0
    merged_by_media = 0
    merged_by_title = 0

    def new_group(idx: int) -> int:
        gid = len(groups)
        groups.append([idx])
        group_of[idx] = gid
        return gid

    def attach(idx: int, gid: int) -> None:
        groups[gid].append(idx)
        group_of[idx] = gid

    for i, rec in enumerate(items):
        url_key = _normalise_url(rec.url)
        media_key = _normalise_url(rec.media_url) if rec.media_url else ""

        gid: int | None = None
        if url_key and url_key in by_url:
            gid = by_url[url_key]
            merged_by_url += 1
        elif media_key and media_key in by_media:
            gid = by_media[media_key]
            merged_by_media += 1

        if gid is None:
            gid = new_group(i)
        else:
            attach(i, gid)

        if url_key:
            by_url.setdefault(url_key, gid)
        if media_key:
            by_media.setdefault(media_key, gid)

    title_shingles = [_shingles(_tokenize(r.title)) for r in items]
    buckets = [_duration_bucket(r.duration_s) for r in items]

    for i in range(len(items)):
        if buckets[i] is None:
            continue
        for j in range(i + 1, len(items)):
            if group_of[i] == group_of[j]:
                continue
            if buckets[j] != buckets[i]:
                continue
            score = _jaccard(title_shingles[i], title_shingles[j])
            if score < _TITLE_JACCARD_THRESHOLD:
                continue
            src_gid = group_of[j]
            dst_gid = group_of[i]
            for k in groups[src_gid]:
                group_of[k] = dst_gid
            groups[dst_gid].extend(groups[src_gid])
            groups[src_gid] = []
            merged_by_title += 1

    survivors: list[VideoRecord] = []
    duplicates: dict[str, list[str]] = {}
    for members in groups:
        if not members:
            continue
        group_records = [items[k] for k in members]
        group_records.sort(key=_survivor_key)
        survivor = group_records[0]
        survivors.append(survivor)
        dup_ids = [r.id for r in group_records[1:]]
        if dup_ids:
            duplicates[survivor.id] = dup_ids

    survivors.sort(key=lambda r: r.id)

    counters = DedupCounters(
        n_input=len(items),
        n_output=len(survivors),
        merged_by_url=merged_by_url,
        merged_by_media_url=merged_by_media,
        merged_by_title=merged_by_title,
    )
    return DedupResult(
        records=survivors,
        duplicates=duplicates,
        counters=counters._asdict(),
    )
