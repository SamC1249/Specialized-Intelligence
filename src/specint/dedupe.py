"""Cross-source near-duplicate detection (metadata-only).

Multiple sources host the same procedural footage (a CC-BY cooking demo
on the Internet Archive and its Wikimedia Commons mirror, for example).
Summing raw per-source counts therefore overstates the true corpus size.

This module clusters records using a cheap, deterministic key:

    key(record) = (normalized_title, duration_bucket)

where `normalized_title` strips accents, lowercases, collapses runs of
non-alphanumeric characters to a single space, and drops a small list of
file-extension suffixes; `duration_bucket` rounds the declared duration
to the nearest 30 seconds (records without a declared duration bucket to
`None`, which only collides with other duration-less records that share
the same title).

We deliberately avoid embedding-based dedupe here — frames are not
downloaded at this stage of the pipeline, and a Jaccard / minhash tier
would be out of scope for the seed PR. The next layer can replace the
`_key` function without changing the public API.

Within a cluster the "winner" is picked by a tiered preference:
  1. license is redistributable (prefer license-clean over UNKNOWN);
  2. higher `quality_score` (falls back to 0 when unset);
  3. longer `duration_s`;
  4. lexicographic `id` (deterministic tie-breaker).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import License, VideoRecord

_FILE_EXT_RE = re.compile(r"\.(webm|ogv|ogg|mp4|mov|mkv|avi|m4v)$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
# Common upstream title prefixes that are metadata noise, not content.
_PREFIX_RE = re.compile(r"^(file|image|video|media)\s*:\s*", re.IGNORECASE)


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", title) if not unicodedata.combining(c)
    ).lower()
    stripped = _PREFIX_RE.sub("", stripped)
    stripped = _FILE_EXT_RE.sub("", stripped)
    stripped = _NON_ALNUM_RE.sub(" ", stripped).strip()
    return stripped


def _duration_bucket(seconds: float | None, bucket_s: float = 30.0) -> int | None:
    if seconds is None or seconds <= 0:
        return None
    return round(seconds / bucket_s)


def _key(record: VideoRecord, bucket_s: float = 30.0) -> tuple[str, int | None]:
    return (_normalize_title(record.title), _duration_bucket(record.duration_s, bucket_s))


def _winner_rank(record: VideoRecord) -> tuple[int, float, float, str]:
    license_clean = 1 if record.license.is_redistributable else 0
    return (
        license_clean,
        float(record.quality_score or 0.0),
        float(record.duration_s or 0.0),
        record.id,
    )


@dataclass(frozen=True)
class Cluster:
    """A group of records judged to be the same underlying video."""

    key: tuple[str, int | None]
    members: tuple[VideoRecord, ...]

    def winner(self) -> VideoRecord:
        return max(self.members, key=_winner_rank)


def cluster(records: Iterable[VideoRecord], bucket_s: float = 30.0) -> list[Cluster]:
    """Group records by (normalized_title, duration_bucket).

    Records whose normalized title is empty are returned as singleton
    clusters so we never collapse a batch of 'untitled' records together.
    """
    groups: dict[tuple[str, int | None], list[VideoRecord]] = {}
    singletons: list[VideoRecord] = []
    for r in records:
        k = _key(r, bucket_s=bucket_s)
        if not k[0]:
            singletons.append(r)
            continue
        groups.setdefault(k, []).append(r)

    clusters: list[Cluster] = [
        Cluster(key=k, members=tuple(sorted(v, key=lambda r: r.id)))
        for k, v in sorted(groups.items())
    ]
    clusters.extend(
        Cluster(key=("", None), members=(r,)) for r in sorted(singletons, key=lambda r: r.id)
    )
    return clusters


def dedupe(records: Iterable[VideoRecord], bucket_s: float = 30.0) -> list[VideoRecord]:
    """Return one representative record per cluster, picking the best
    member per `_winner_rank`."""
    return [c.winner() for c in cluster(records, bucket_s=bucket_s)]


def dedupe_stats(records: Iterable[VideoRecord], bucket_s: float = 30.0) -> dict[str, int]:
    """Return a small, JSON-serializable summary of the dedupe outcome."""
    items = list(records)
    clusters = cluster(items, bucket_s=bucket_s)
    duplicates = sum(len(c.members) - 1 for c in clusters)
    license_clean_before = sum(1 for r in items if r.license.is_redistributable)
    winners = [c.winner() for c in clusters]
    license_clean_after = sum(1 for r in winners if r.license.is_redistributable)
    return {
        "n_records": len(items),
        "n_clusters": len(clusters),
        "n_duplicates_removed": duplicates,
        "n_license_clean_before": license_clean_before,
        "n_license_clean_after": license_clean_after,
    }


__all__ = [
    "Cluster",
    "License",
    "cluster",
    "dedupe",
    "dedupe_stats",
]
