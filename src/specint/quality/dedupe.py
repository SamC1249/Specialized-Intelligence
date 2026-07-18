"""Cross-source dedupe.

Same underlying recipe can appear on Wikimedia Commons *and* be mirrored
on Internet Archive *and* be embedded in a PeerTube post. Left un-deduped
this triple-counts yield and biases the harness.

Algorithm (two-signal-minimum, deliberately conservative):

  1. Compute several *keys* per record: normalized title, media-URL host+path
     hash, `(title, author)` tuple, `(title, duration-bucket)` tuple.
  2. Build an undirected graph where nodes are records and edges connect
     records that share at least ONE key AND agree on at least one other
     signal (author OR duration-bucket OR media-URL host).
  3. Cluster via union-find. One canonical record per cluster: prefer the
     more permissive license, then higher `quality_score`, then longer
     `duration_s`.
  4. Emit `DedupeReport` with cluster stats — never silently drop records.

Intentionally NO fuzzy string matching; that will land after we have a
labeled set of true-positive pairs.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from specint.records import License, VideoRecord

_LICENSE_PRIORITY: dict[License, int] = {
    License.CC0: 6,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}

_TITLE_CLEAN_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)


def _norm_title(title: str) -> str:
    t = title.casefold().strip()
    t = _TITLE_CLEAN_RE.sub(" ", t)
    return " ".join(t.split())


def _duration_bucket(record: VideoRecord) -> str | None:
    d = record.duration_s
    if d is None or d <= 0:
        return None
    return f"{int(d // 15)}"  # 15-second buckets


def _media_hash(record: VideoRecord) -> str | None:
    if record.media_url is None:
        return None
    s = str(record.media_url)
    payload = s.split("://", 1)[-1].rstrip("/").casefold()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _keys(record: VideoRecord) -> dict[str, str]:
    keys: dict[str, str] = {}
    title = _norm_title(record.title)
    if title:
        keys["title"] = title
        if record.author:
            keys["title_author"] = f"{title}|{record.author.casefold()}"
        bucket = _duration_bucket(record)
        if bucket is not None:
            keys["title_duration"] = f"{title}|{bucket}"
    mh = _media_hash(record)
    if mh:
        keys["media"] = mh
    return keys


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _shared_signals(a: VideoRecord, b: VideoRecord) -> int:
    signals = 0
    if _norm_title(a.title) and _norm_title(a.title) == _norm_title(b.title):
        signals += 1
    if a.author and b.author and a.author.casefold() == b.author.casefold():
        signals += 1
    ab, bb = _duration_bucket(a), _duration_bucket(b)
    if ab is not None and ab == bb:
        signals += 1
    mha, mhb = _media_hash(a), _media_hash(b)
    if mha and mha == mhb:
        signals += 2
    return signals


def _canonical(records: list[VideoRecord]) -> VideoRecord:
    def _key(r: VideoRecord) -> tuple[int, float, float]:
        return (
            _LICENSE_PRIORITY.get(r.license, 0),
            r.quality_score or 0.0,
            r.duration_s or 0.0,
        )

    return max(records, key=_key)


@dataclass(frozen=True)
class DedupeCluster:
    canonical_id: str
    member_ids: tuple[str, ...]
    sources: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DedupeReport:
    input_n: int
    output_n: int
    n_clusters_gt1: int
    clusters: tuple[DedupeCluster, ...] = field(default_factory=tuple)

    @property
    def reduction(self) -> float:
        if self.input_n == 0:
            return 0.0
        return 1.0 - (self.output_n / self.input_n)


def dedupe(records: Iterable[VideoRecord]) -> tuple[list[VideoRecord], DedupeReport]:
    items = list(records)
    n = len(items)
    if n == 0:
        return [], DedupeReport(0, 0, 0)

    uf = _UnionFind(n)
    key_index: dict[str, list[int]] = {}
    per_record_keys = [_keys(r) for r in items]
    for idx, keys in enumerate(per_record_keys):
        for k in keys.values():
            key_index.setdefault(k, []).append(idx)

    for candidates in key_index.values():
        if len(candidates) < 2:
            continue
        anchor = candidates[0]
        for other in candidates[1:]:
            if _shared_signals(items[anchor], items[other]) >= 2:
                uf.union(anchor, other)

    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        clusters.setdefault(uf.find(idx), []).append(idx)

    canonical: list[VideoRecord] = []
    reports: list[DedupeCluster] = []
    for members in clusters.values():
        cluster_records = [items[i] for i in members]
        winner = _canonical(cluster_records)
        canonical.append(winner)
        if len(members) > 1:
            reports.append(
                DedupeCluster(
                    canonical_id=winner.id,
                    member_ids=tuple(sorted(r.id for r in cluster_records)),
                    sources=tuple(sorted({r.source for r in cluster_records})),
                    reason="≥2 shared signals (title/author/duration/media)",
                )
            )

    canonical.sort(key=lambda r: r.id)
    return canonical, DedupeReport(
        input_n=n,
        output_n=len(canonical),
        n_clusters_gt1=len(reports),
        clusters=tuple(reports),
    )
