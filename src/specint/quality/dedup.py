"""Metadata-only near-duplicate collapse.

We are pre-download, so we cannot perceptually hash frames. Instead we
apply two cheap, conservative rules and expose the result via the compare
harness (opt-in). See `docs/artifacts/videohash-perceptual-dedup.md` for
the follow-up plan once we start downloading media.

Rules (both must be true for two records to merge):
  * normalized-title equality (case-fold, strip punctuation & whitespace);
  * *at least one* of: same author, same normalized URL host, same
    `source_native_id` prefix (last 8 chars — catches Commons re-uploads).

Merging keeps the record with the highest `quality_score` (breaking ties
by source order in `PREFERRED_SOURCE_ORDER`) and appends the discarded
IDs to `duplicate_of`. Because `VideoRecord` is frozen-ish we return a
fresh list; callers can compute counts before/after to size the collapse.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from urllib.parse import urlparse

from specint.records import VideoRecord

_TITLE_STRIP = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")

PREFERRED_SOURCE_ORDER: tuple[str, ...] = (
    "wikimedia",
    "archive_org",
    "peertube",
    "common_crawl",
)


def _normalize_title(title: str) -> str:
    folded = unicodedata.normalize("NFKC", title).casefold()
    stripped = _TITLE_STRIP.sub(" ", folded)
    return _WS.sub(" ", stripped).strip()


def _host(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except ValueError:
        return ""


def _co_signals(a: VideoRecord, b: VideoRecord) -> bool:
    if a.author and b.author and a.author.strip().casefold() == b.author.strip().casefold():
        return True
    if _host(str(a.url)) and _host(str(a.url)) == _host(str(b.url)):
        return True
    tail_a = a.source_native_id[-8:] if a.source_native_id else ""
    tail_b = b.source_native_id[-8:] if b.source_native_id else ""
    return bool(tail_a and tail_a == tail_b)


def _rank(record: VideoRecord) -> tuple[float, int]:
    order_idx = (
        PREFERRED_SOURCE_ORDER.index(record.source)
        if record.source in PREFERRED_SOURCE_ORDER
        else len(PREFERRED_SOURCE_ORDER)
    )
    return (-(record.quality_score or 0.0), order_idx)


def dedupe_by_id_and_title(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Collapse near-duplicates by normalized title + one corroborating signal.

    Exact `id` collisions are always dropped first (keeping the first
    occurrence's order-stable position).
    """
    items = list(records)
    if not items:
        return []

    seen_ids: dict[str, VideoRecord] = {}
    for r in items:
        seen_ids.setdefault(r.id, r)
    deduped_by_id: list[VideoRecord] = list(seen_ids.values())

    buckets: dict[str, list[VideoRecord]] = {}
    for r in deduped_by_id:
        buckets.setdefault(_normalize_title(r.title), []).append(r)

    out: list[VideoRecord] = []
    for bucket in buckets.values():
        if len(bucket) == 1:
            out.append(bucket[0])
            continue
        surviving: list[VideoRecord] = []
        for r in bucket:
            if any(_co_signals(r, s) for s in surviving):
                incumbent = next(s for s in surviving if _co_signals(r, s))
                if _rank(r) < _rank(incumbent):
                    surviving = [x for x in surviving if x is not incumbent]
                    surviving.append(r)
                continue
            surviving.append(r)
        out.extend(surviving)

    out.sort(key=lambda r: (r.source, r.id))
    return out


def dedupe_stats(before: Sequence[VideoRecord], after: Sequence[VideoRecord]) -> dict[str, int]:
    return {
        "n_before": len(before),
        "n_after": len(after),
        "n_collapsed": len(before) - len(after),
    }
