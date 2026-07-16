"""Cross-source record deduplication (metadata only).

The default `run_comparison` collapses duplicate `VideoRecord.id`s
within a single source slug — that catches PeerTube federation
double-counts and identical rows re-emitted by a flaky adapter.

Cross-source dedup (same clip mirrored on Wikimedia *and* Internet
Archive) requires a canonicalisation step. We do not enable it by
default because the canonicalisation policy is still evolving:
the rule below is intentionally conservative — same declared media
URL host+path, or same (normalised title, duration bucket, author).

If two records match, the winner is the one with the higher-tier
license, breaking ties by ``VideoRecord.id`` lexicographic order.
This is pure, deterministic, and offline-testable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from specint.records import License, VideoRecord

_LICENSE_TIER: dict[License, int] = {
    License.CC0: 6,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}


def _license_rank(record: VideoRecord) -> int:
    return _LICENSE_TIER.get(record.license, 0)


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _normalise_title(title: str) -> str:
    tokens = [t.lower() for t in _WORD_RE.findall(title or "")]
    return " ".join(tokens)


def _media_key(record: VideoRecord) -> str | None:
    if not record.media_url:
        return None
    parsed = urlparse(str(record.media_url))
    return f"{parsed.netloc.lower()}{parsed.path.lower()}" or None


def _duration_bucket(duration_s: float | None) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return int(duration_s // 10)


@dataclass(frozen=True)
class DedupReport:
    records: list[VideoRecord]
    removed: list[tuple[str, str]]  # (dropped_id, kept_id)

    @property
    def n_removed(self) -> int:
        return len(self.removed)


def dedup_records(records: Iterable[VideoRecord]) -> DedupReport:
    """Deduplicate across arbitrary sources.

    The dedup key is either the canonical media URL host+path, or a
    (normalised title, duration bucket, author) tuple when both fields
    are present. Records without enough evidence to key on stay
    untouched.
    """

    items = list(records)
    kept_by_key: dict[str, VideoRecord] = {}
    keep: dict[str, VideoRecord] = {}
    removed: list[tuple[str, str]] = []

    def _prefer(existing: VideoRecord, candidate: VideoRecord) -> VideoRecord:
        if _license_rank(candidate) > _license_rank(existing):
            return candidate
        if _license_rank(candidate) < _license_rank(existing):
            return existing
        return existing if existing.id <= candidate.id else candidate

    def _collision_keys(record: VideoRecord) -> list[str]:
        keys: list[str] = []
        media = _media_key(record)
        if media:
            keys.append(f"media::{media}")
        title = _normalise_title(record.title)
        bucket = _duration_bucket(record.duration_s)
        author = (record.author or "").strip().lower()
        if title and bucket is not None and author:
            keys.append(f"t3::{title}|{bucket}|{author}")
        return keys

    order: dict[str, int] = {}
    for idx, record in enumerate(items):
        collision_keys = _collision_keys(record)
        if not collision_keys:
            keep[record.id] = record
            order.setdefault(record.id, idx)
            continue
        rival: VideoRecord | None = None
        rival_key: str | None = None
        for key in collision_keys:
            if key in kept_by_key:
                rival = kept_by_key[key]
                rival_key = key
                break
        if rival is None:
            for key in collision_keys:
                kept_by_key[key] = record
            keep[record.id] = record
            order.setdefault(record.id, idx)
            continue

        winner = _prefer(rival, record)
        if winner.id == rival.id:
            removed.append((record.id, rival.id))
        else:
            removed.append((rival.id, record.id))
            keep.pop(rival.id, None)
            for key, existing_rec in list(kept_by_key.items()):
                if existing_rec.id == rival.id:
                    kept_by_key[key] = winner
            for key in collision_keys:
                kept_by_key[key] = winner
            keep[winner.id] = winner
            order.setdefault(winner.id, idx)
        if rival_key is not None and winner.id == rival.id:
            for key in collision_keys:
                kept_by_key.setdefault(key, winner)

    survivors = sorted(keep.values(), key=lambda r: (order.get(r.id, 0), r.id))
    return DedupReport(records=survivors, removed=removed)
