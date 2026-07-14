"""Cross-source deduplication for `VideoRecord` streams.

Two records are considered duplicates when either:

1. They share a canonical URL after normalization (lowercased host,
   stripped query/fragment, no trailing slash), OR
2. Their normalized titles agree AND their duration_s falls in the same
   5-second bucket.

Normalization for titles: lowercased, non-alphanumeric replaced by
whitespace, whitespace-collapsed (single spaces), stopwords not
removed (we don't want "Pasta" ≈ "Pasta with Garlic and Prawns").

Tie-breaks (deterministic):
  - Prefer records with a redistributable license.
  - Then higher `quality_score` (None → 0.0).
  - Then lexicographically smaller `id`.

Implementation uses union-find so that transitively-linked records
across multiple keys collapse into one cluster and only the best
record per cluster survives. This avoids the "loser still hides
under its own URL key" bug that a naive first-write-wins map hits.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from specint.records import VideoRecord

_TITLE_NONALPHA = re.compile(r"[^0-9a-zA-Z]+")


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def normalize_title(title: str) -> str:
    return _TITLE_NONALPHA.sub(" ", (title or "").lower()).strip()


def _rank(r: VideoRecord) -> tuple[int, float, str]:
    return (
        1 if r.license.is_redistributable else 0,
        r.quality_score or 0.0,
        r.id,
    )


def _better(a: VideoRecord, b: VideoRecord) -> VideoRecord:
    ra, rb = _rank(a), _rank(b)
    if ra[:2] == rb[:2]:
        return a if a.id <= b.id else b
    return a if ra > rb else b


def dedupe_records(records: list[VideoRecord]) -> tuple[list[VideoRecord], int]:
    """Return (unique_records, n_dropped)."""
    n = len(records)
    if n == 0:
        return [], 0

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    url_idx: dict[str, int] = {}
    title_idx: dict[tuple[str, object], int] = {}
    for i, r in enumerate(records):
        url_key = normalize_url(str(r.url))
        title_key = normalize_title(r.title)
        dur = float(r.duration_s if r.duration_s is not None else -1.0)
        bucket: object = round(dur / 5.0) if dur >= 0 else "na"
        title_bucket = (title_key, bucket)

        if title_key:
            if title_bucket in title_idx:
                union(i, title_idx[title_bucket])
            else:
                title_idx[title_bucket] = i

        if url_key in url_idx:
            union(i, url_idx[url_key])
        else:
            url_idx[url_key] = i

    groups: dict[int, list[VideoRecord]] = {}
    for i, rec in enumerate(records):
        groups.setdefault(find(i), []).append(rec)

    winners: list[VideoRecord] = []
    for group in groups.values():
        w = group[0]
        for r in group[1:]:
            w = _better(w, r)
        winners.append(w)

    winners.sort(key=lambda r: r.id)
    return winners, n - len(winners)
