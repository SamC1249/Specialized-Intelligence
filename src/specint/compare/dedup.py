"""Cross-source duplicate detection.

The comparison harness's `__total__` row sums `n_records` across sources,
which over-counts when the same video is exposed by more than one source
(e.g. a Wikimedia Commons item mirrored on a PeerTube instance).

This module surfaces likely duplicates with an intentionally conservative
blocking key: normalized title + duration bucket. False positives here
are worse than false negatives — we would rather under-report dedup than
silently drop a distinct video.

Blocking key:
  - Title: lowercased, punctuation stripped, whitespace collapsed,
           optional file extension (.webm/.ogv/.mp4) dropped, leading
           "file:" MediaWiki prefix dropped.
  - Duration bucket: `round(duration_s / 30) * 30` (30 s buckets).
    Records with unknown duration go into bucket `None`, which is
    matched only against other unknown-duration records.

Output: `DedupReport` with per-cluster metadata + a top-level count of
collapsed records, safe to serialise into the sweep JSON.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_EXTS = (".webm", ".ogv", ".ogg", ".mp4", ".mkv", ".mov")
_FILE_PREFIXES = ("file:", "datei:", "archivo:", "fichier:")


def normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.strip().lower()
    for prefix in _FILE_PREFIXES:
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
    for ext in _EXTS:
        if t.endswith(ext):
            t = t[: -len(ext)]
            break
    t = _PUNCT_RE.sub(" ", t)
    return " ".join(t.split())


def duration_bucket(duration_s: float | None, width_s: float = 30.0) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    if width_s <= 0:
        return int(duration_s)
    return int(round(duration_s / width_s) * width_s)


def blocking_key(record: VideoRecord) -> tuple[str, int | None]:
    return normalize_title(record.title), duration_bucket(record.duration_s)


class DedupCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_title: str
    duration_bucket: int | None
    record_ids: list[str]
    sources: list[str]


class DedupReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_records_in: int
    n_records_out: int
    n_duplicates_collapsed: int
    n_cross_source_clusters: int
    clusters: list[DedupCluster]

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def find_clusters(records: list[VideoRecord]) -> list[DedupCluster]:
    buckets: dict[tuple[str, int | None], list[VideoRecord]] = defaultdict(list)
    for r in records:
        key = blocking_key(r)
        if not key[0]:
            continue
        buckets[key].append(r)

    clusters: list[DedupCluster] = []
    for (title, bucket), items in buckets.items():
        if len(items) < 2:
            continue
        clusters.append(
            DedupCluster(
                normalized_title=title,
                duration_bucket=bucket,
                record_ids=sorted(r.id for r in items),
                sources=sorted({r.source for r in items}),
            )
        )
    clusters.sort(key=lambda c: (c.normalized_title, c.duration_bucket or -1))
    return clusters


def build_report(records: list[VideoRecord]) -> DedupReport:
    clusters = find_clusters(records)
    collapsed = sum(len(c.record_ids) - 1 for c in clusters)
    cross_source = sum(1 for c in clusters if len(c.sources) > 1)
    return DedupReport(
        n_records_in=len(records),
        n_records_out=len(records) - collapsed,
        n_duplicates_collapsed=collapsed,
        n_cross_source_clusters=cross_source,
        clusters=clusters,
    )
