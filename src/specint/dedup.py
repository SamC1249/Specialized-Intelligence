"""Cross-source deduplication.

The same permanently-licensed asset frequently appears under more than
one source (e.g. an Internet Archive item that mirrors a Wikimedia
Commons upload, a PeerTube instance that re-hosts a public-domain NASA
clip). Counting those twice would (a) inflate our yield numbers and
(b) train models on repeated frames.

The fingerprint is intentionally coarse-but-deterministic:

    normalized_title x duration_bucket_seconds x author_slug

`author_slug` is included so that two unrelated 5-minute demos titled
"Chocolate cake" by different teachers do not collide. When authors
differ but everything else matches we keep both records (safer default:
a false-negative here just leaves a real dupe in the corpus; a
false-positive drops legitimate data).

`dedupe()` is a pure function on a list of already-scored records. The
higher-quality record wins ties; ties on quality are broken by
`(source, id)` to keep the output deterministic across runs.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from specint.records import VideoRecord

DUPLICATE_DURATION_BUCKET_S: float = 5.0
_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_WS_RE = re.compile(r"\s+")
_VIDEO_EXT_RE = re.compile(r"\.(webm|mp4|ogv|mkv|mov|avi|m4v|ogg)$")


def normalize_title(title: str) -> str:
    """Lowercase, strip diacritics, drop file-noise, collapse whitespace.

    Wikimedia Commons titles begin with ``File:`` and end with a video
    extension; archive.org / peertube titles do not. Stripping both
    lets the dedup fingerprint match the same asset across sources.
    """
    if not title:
        return ""
    n = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    n = n.lower()
    n = _VIDEO_EXT_RE.sub("", n)
    n = _PUNCT_RE.sub(" ", n)
    n = _WS_RE.sub(" ", n).strip()
    if n.startswith("file "):
        n = n[5:].lstrip()
    return n


def author_slug(author: str | None) -> str:
    if not author:
        return ""
    return normalize_title(author)


def duration_bucket(duration_s: float | None, bucket: float = DUPLICATE_DURATION_BUCKET_S) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return int(duration_s // bucket)


def fingerprint(record: VideoRecord) -> tuple[str, int, str]:
    return (
        normalize_title(record.title),
        duration_bucket(record.duration_s),
        author_slug(record.author),
    )


class DuplicateGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint: tuple[str, int, str]
    kept_id: str
    dropped_ids: list[str]


class DedupReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_in: int
    n_out: int
    n_dropped: int
    duplicate_rate: float
    groups: list[DuplicateGroup]


def _preference_key(record: VideoRecord) -> tuple[float, str, str]:
    # Higher quality wins; if tied, lower (source, id) wins for
    # determinism. Negative quality so `min()` picks the "best".
    return (-(record.quality_score or 0.0), record.source, record.id)


def dedupe(
    records: Iterable[VideoRecord],
) -> tuple[list[VideoRecord], DedupReport]:
    items = list(records)
    if not items:
        return [], DedupReport(n_in=0, n_out=0, n_dropped=0, duplicate_rate=0.0, groups=[])

    buckets: dict[tuple[str, int, str], list[VideoRecord]] = {}
    for r in items:
        fp = fingerprint(r)
        # Records with unusable fingerprints (empty title AND unknown
        # duration AND unknown author) are always unique — skip
        # bucketing to avoid mass-collapsing them.
        if fp == ("", -1, ""):
            buckets[("__unique__", -1, r.id)] = [r]
            continue
        buckets.setdefault(fp, []).append(r)

    kept: list[VideoRecord] = []
    groups: list[DuplicateGroup] = []
    for fp, members in buckets.items():
        if len(members) == 1:
            kept.append(members[0])
            continue
        winner = min(members, key=_preference_key)
        kept.append(winner)
        dropped_ids = sorted(m.id for m in members if m.id != winner.id)
        groups.append(DuplicateGroup(fingerprint=fp, kept_id=winner.id, dropped_ids=dropped_ids))

    kept.sort(key=lambda r: (r.source, r.id))
    n_in = len(items)
    n_out = len(kept)
    n_dropped = n_in - n_out
    duplicate_rate = n_dropped / n_in if n_in else 0.0
    report = DedupReport(
        n_in=n_in,
        n_out=n_out,
        n_dropped=n_dropped,
        duplicate_rate=duplicate_rate,
        groups=groups,
    )
    return kept, report
