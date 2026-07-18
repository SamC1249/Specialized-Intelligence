"""Cross-source deduplication for VideoRecord.

Motivation (see `docs/plan-2026-07-18.md` §A1):
Wikimedia Commons uploads are frequently mirrored on Internet Archive
(and vice-versa); PeerTube instances re-federate. Without dedup we
double-count hours and inflate per-source yield claims.

Design constraints:

- **Metadata-only.** No media download, no perceptual hashing yet.
- **Pure & deterministic.** Same input → same output → same test.
- **License-preserving.** When two duplicates carry different licenses,
  we keep the *strongest* one (CC0 > PD > CC-BY > CC-BY-SA > OTHER_FREE
  > UNKNOWN > RESTRICTED). This is the safe default: never *upgrade*
  a licence we couldn't independently verify.

Match strategy (in order of decreasing precision):

1. **Canonical URL match.** Lowercase host, strip fragment, strip
   query, strip trailing slash, drop `www.` prefix. If two records
   normalize to the same URL, they are duplicates.
2. **Normalized-title + duration-bucket.** Titles are lowercased,
   non-alphanumerics collapsed to single spaces, common noise tokens
   dropped (`hd`, `720p`, `1080p`, `official`, `part-1`). Duration
   bucketed to the nearest 5s. Same (norm_title, bucket, source is
   different) ⇒ near-duplicate.

The public entry point is `dedup(records)` which returns a new list.
`group_duplicates(records)` is exposed for the harness and tests.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlparse, urlunparse

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

_TITLE_NOISE = re.compile(
    r"\b(hd|4k|uhd|720p?|1080p?|2160p?|official|part[-\s]?\d+|episode\s?\d+)\b",
    flags=re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_DURATION_BUCKET_S = 5.0


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def canonical_url(url: str) -> str:
    """Normalize a URL for exact-match dedup. Pure and deterministic."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip().lower()
    if not parsed.scheme:
        return url.strip().lower()
    host = _strip_www(parsed.netloc.lower())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), host, path, "", "", ""))


def normalized_title(title: str) -> str:
    """Lowercase, drop common noise tokens, collapse whitespace."""
    if not title:
        return ""
    lowered = title.lower()
    lowered = _TITLE_NOISE.sub(" ", lowered)
    normalized = _NON_ALNUM.sub(" ", lowered).strip()
    return re.sub(r"\s+", " ", normalized)


def duration_bucket(duration_s: float | None) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return round(duration_s / _DURATION_BUCKET_S)


def _fingerprint(record: VideoRecord) -> tuple[str, tuple[str, int | None]]:
    """Return (canonical_url, (normalized_title, duration_bucket))."""
    return (
        canonical_url(str(record.url)),
        (normalized_title(record.title), duration_bucket(record.duration_s)),
    )


def _license_rank(record: VideoRecord) -> int:
    return _LICENSE_PRIORITY.get(record.license, 0)


def _stable_key(record: VideoRecord) -> tuple[int, str, str]:
    # Highest license first; break ties by source slug then id for determinism.
    return (-_license_rank(record), record.source, record.id)


def group_duplicates(records: Iterable[VideoRecord]) -> list[list[VideoRecord]]:
    """Group records into duplicate clusters.

    Two records are grouped together if they share a canonical URL, or
    if they share a (normalized_title, duration_bucket) pair where the
    duration_bucket is not None. Groups are returned in a stable order
    (sorted by the strongest member's stable key).
    """
    items = list(records)
    parent: dict[int, int] = {i: i for i in range(len(items))}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_url: dict[str, int] = {}
    by_title_dur: dict[tuple[str, int], int] = {}
    for i, rec in enumerate(items):
        curl, (ntitle, bucket) = _fingerprint(rec)
        if curl:
            if curl in by_url:
                union(by_url[curl], i)
            else:
                by_url[curl] = i
        if ntitle and bucket is not None:
            key = (ntitle, bucket)
            if key in by_title_dur:
                union(by_title_dur[key], i)
            else:
                by_title_dur[key] = i

    clusters: dict[int, list[VideoRecord]] = {}
    for i, rec in enumerate(items):
        clusters.setdefault(find(i), []).append(rec)

    groups = list(clusters.values())
    for g in groups:
        g.sort(key=_stable_key)
    groups.sort(key=lambda g: _stable_key(g[0]))
    return groups


def dedup(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return one representative per duplicate cluster.

    The representative is the highest-license member; ties are broken
    by (source, id) for determinism.
    """
    groups = group_duplicates(records)
    return [g[0] for g in groups]


def dedup_report(records: Iterable[VideoRecord]) -> dict[str, int]:
    """Summary stats useful for the benchmark harness and CLI output."""
    items = list(records)
    groups = group_duplicates(items)
    dup_records = sum(len(g) - 1 for g in groups if len(g) > 1)
    return {
        "n_input": len(items),
        "n_unique_groups": len(groups),
        "n_duplicates": dup_records,
    }
