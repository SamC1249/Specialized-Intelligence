"""Cross-source deduplication.

Deterministic collapse of near-duplicate `VideoRecord`s so that
`__total__` counts stop over-counting the same government-produced
cooking demo that appears on Internet Archive, Wikimedia Commons, and a
PeerTube mirror.

Design:
  - Dedup key = (normalize_title(title), duration_bucket(duration_s)).
  - We keep the highest-quality record as the survivor. Ties break by
    preferring the record with a more redistributable license, then by
    the earlier record id (stable ordering).
  - Every dropped record's URL and license is retained on the
    survivor's `DedupCluster` so provenance is never silently lost.
  - Records whose duration is unknown *and* whose title normalises to
    an empty string are never merged with anything else (safety).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from specint.records import License, VideoRecord

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

_LICENSE_RANK: dict[License, int] = {
    License.CC0: 6,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}


def normalize_title(title: str) -> str:
    """Lowercase, strip diacritics, collapse to a-z0-9 tokens."""
    if not title:
        return ""
    stripped = unicodedata.normalize("NFKD", title)
    stripped = "".join(c for c in stripped if not unicodedata.combining(c))
    return _NORMALIZE_RE.sub(" ", stripped.lower()).strip()


def duration_bucket(seconds: float | None, width_s: float = 30.0) -> int:
    """30-second buckets by default; `None` → -1 (own bucket)."""
    if seconds is None or seconds <= 0:
        return -1
    return int(seconds // width_s)


def _dedup_key(record: VideoRecord) -> tuple[str, int] | None:
    title = normalize_title(record.title)
    bucket = duration_bucket(record.duration_s)
    if not title and bucket == -1:
        return None
    return (title, bucket)


@dataclass(frozen=True)
class DedupCluster:
    key: tuple[str, int]
    survivor_id: str
    member_ids: tuple[str, ...]
    member_urls: tuple[str, ...]
    member_sources: tuple[str, ...]
    member_licenses: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "key_title": self.key[0],
            "key_duration_bucket": self.key[1],
            "survivor_id": self.survivor_id,
            "member_ids": list(self.member_ids),
            "member_urls": list(self.member_urls),
            "member_sources": list(self.member_sources),
            "member_licenses": list(self.member_licenses),
        }


@dataclass
class _Bucket:
    key: tuple[str, int]
    members: list[VideoRecord] = field(default_factory=list)


def _survivor_sort_key(record: VideoRecord) -> tuple[float, int, str]:
    quality = record.quality_score if record.quality_score is not None else 0.0
    license_rank = _LICENSE_RANK.get(record.license, 0)
    return (-quality, -license_rank, record.id)


def dedup_records(
    records: Iterable[VideoRecord],
    max_cluster_size: int = 3,
) -> tuple[list[VideoRecord], list[DedupCluster]]:
    """Return `(survivors, clusters)`.

    `clusters` contains only clusters where at least two records were
    merged. Singletons are not reported. If a cluster would exceed
    `max_cluster_size`, we refuse to merge past that size unless the
    author is identical across all members (mitigation for templated
    titles like "Cooking, part 1..N").
    """
    records = list(records)
    buckets: dict[tuple[str, int], _Bucket] = {}
    unkeyed: list[VideoRecord] = []
    for rec in records:
        key = _dedup_key(rec)
        if key is None:
            unkeyed.append(rec)
            continue
        buckets.setdefault(key, _Bucket(key=key)).members.append(rec)

    survivors: list[VideoRecord] = []
    clusters: list[DedupCluster] = []
    for key, bucket in buckets.items():
        members = bucket.members
        if len(members) > max_cluster_size:
            authors = {m.author for m in members if m.author}
            if len(authors) != 1:
                for rec in members:
                    survivors.append(rec)
                continue
        if len(members) == 1:
            survivors.append(members[0])
            continue
        sorted_members = sorted(members, key=_survivor_sort_key)
        survivor = sorted_members[0]
        survivors.append(survivor)
        clusters.append(
            DedupCluster(
                key=key,
                survivor_id=survivor.id,
                member_ids=tuple(m.id for m in sorted_members),
                member_urls=tuple(str(m.url) for m in sorted_members),
                member_sources=tuple(m.source for m in sorted_members),
                member_licenses=tuple(m.license.value for m in sorted_members),
            )
        )

    survivors.extend(unkeyed)
    survivors.sort(key=lambda r: r.id)
    clusters.sort(key=lambda c: c.survivor_id)
    return survivors, clusters
