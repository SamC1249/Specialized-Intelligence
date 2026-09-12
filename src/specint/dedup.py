"""Cross-source deduplication.

Two records are considered duplicates when either:

  1. They share a normalised landing URL (host + path, lowercased,
     trailing slash stripped, query dropped), OR
  2. Their normalised titles are equal AND either duration matches
     within 2s or one of them is missing duration.

Ordering is deterministic: whichever record has the higher
`quality_score` wins; ties break on `(source, id)` alphabetically so
the harness output is reproducible.

Kept intentionally cheap so we can run it inline in `run_comparison`
over millions of candidates. If we ever need fuzzy title matching, do
it in a separate module and benchmark it against this one before
switching.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from specint.records import VideoRecord

_WORD_RE = re.compile(r"[a-z0-9]+")


_TRACKING_PARAMS: frozenset[str] = frozenset(
    {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
)


def _normalize_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return url.lower()
    host = (parts.hostname or "").lower()
    path = (parts.path or "").rstrip("/").lower()
    query_pairs: list[tuple[str, str]] = []
    if parts.query:
        for chunk in parts.query.split("&"):
            if not chunk:
                continue
            k, _, v = chunk.partition("=")
            if k.lower() in _TRACKING_PARAMS:
                continue
            query_pairs.append((k.lower(), v.lower()))
    query_pairs.sort()
    query = "&".join(f"{k}={v}" for k, v in query_pairs)
    return f"{host}{path}?{query}" if query else f"{host}{path}"


def _normalize_title(title: str) -> str:
    tokens = _WORD_RE.findall((title or "").lower())
    return " ".join(tokens)


def _duration_match(a: float | None, b: float | None, tol_s: float = 2.0) -> bool:
    if a is None or b is None:
        return True
    return abs(a - b) <= tol_s


def _key_score(record: VideoRecord) -> tuple[float, str, str]:
    q = record.quality_score if record.quality_score is not None else -1.0
    return (q, record.source, record.id)


@dataclass(frozen=True)
class DedupResult:
    kept: list[VideoRecord]
    removed: list[VideoRecord]

    @property
    def n_removed(self) -> int:
        return len(self.removed)


def deduplicate(records: Iterable[VideoRecord]) -> DedupResult:
    items = sorted(records, key=_key_score, reverse=True)
    kept_by_url: dict[str, VideoRecord] = {}
    kept_by_title: dict[str, VideoRecord] = {}
    kept: list[VideoRecord] = []
    removed: list[VideoRecord] = []

    for r in items:
        url_key = _normalize_url(str(r.url))
        title_key = _normalize_title(r.title)

        dup = kept_by_url.get(url_key)
        if dup is None and title_key:
            candidate = kept_by_title.get(title_key)
            if candidate is not None and _duration_match(candidate.duration_s, r.duration_s):
                dup = candidate

        if dup is not None:
            removed.append(r)
            continue

        kept.append(r)
        if url_key:
            kept_by_url[url_key] = r
        if title_key:
            kept_by_title.setdefault(title_key, r)

    kept.sort(key=lambda r: (r.source, r.id))
    return DedupResult(kept=kept, removed=removed)


__all__ = ["DedupResult", "deduplicate"]
