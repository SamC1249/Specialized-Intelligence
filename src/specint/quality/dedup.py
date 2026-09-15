"""Cross-source deduplication for `VideoRecord` streams.

Motivation (H2 in `docs/plan-2026-09-15.md`): the `__total__` row emitted
by the seed comparison harness double-counts videos that appear on more
than one upstream (e.g. a Blender PD short mirrored on Wikimedia Commons
*and* the Internet Archive). Real "yield" is the unique count.

We use three collision keys, in decreasing order of confidence:

  1. `media_url` — same direct file URL is nearly certainly the same clip.
  2. Canonical landing `url` (scheme-stripped, trailing slash removed).
  3. Fingerprint of `(canonical_title, duration_bucket_10s,
     author_normalised)` — catches the common "same clip re-uploaded to
     a second host" case. Records with unknown duration deliberately do
     not participate in fingerprint bucketing to avoid over-collision.

The dedup routine returns a `DedupReport` and a deduped list. The report
carries the source-by-source collision matrix so we can see *where* the
overlaps come from (e.g. `wikimedia`/`archive_org` mirroring).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from specint.records import VideoRecord

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")


def _ascii_fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def canonical_title(title: str) -> str:
    """Lowercased, ASCII-folded, punctuation-stripped, whitespace-collapsed."""
    folded = _ascii_fold(title or "").lower()
    folded = _PUNCT_RE.sub(" ", folded)
    folded = _WHITESPACE_RE.sub(" ", folded).strip()
    return folded


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    u = str(url).strip().lower()
    for prefix in ("http://", "https://"):
        if u.startswith(prefix):
            u = u[len(prefix) :]
            break
    return u.rstrip("/") or None


def normalise_author(author: str | None) -> str:
    if not author:
        return ""
    return _WHITESPACE_RE.sub(" ", _ascii_fold(author).lower()).strip()


def _duration_bucket(duration_s: float | None) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return int(duration_s // 10)


def content_fingerprint(record: VideoRecord) -> str | None:
    """Return a stable fingerprint or `None` if the record is too thin."""
    title = canonical_title(record.title)
    bucket = _duration_bucket(record.duration_s)
    author = normalise_author(record.author)
    if not title or bucket is None:
        return None
    return f"title={title}|dur10={bucket}|author={author}"


class DedupReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_input: int
    n_unique: int
    n_collisions: int
    collisions_by_key: dict[str, int] = Field(default_factory=dict)
    collision_matrix: dict[str, int] = Field(default_factory=dict)
    per_source_unique: dict[str, int] = Field(default_factory=dict)


def _pair_key(a: str, b: str) -> str:
    lo, hi = sorted([a, b])
    return f"{lo}::{hi}"


def deduplicate(records: Iterable[VideoRecord]) -> tuple[list[VideoRecord], DedupReport]:
    """Deduplicate a stream, preferring the first-seen record for each key.

    "First-seen" is a deterministic function of iteration order, so
    caller determines precedence (typically sort by source-quality
    ranking before calling).
    """
    items = list(records)
    seen_media: dict[str, VideoRecord] = {}
    seen_url: dict[str, VideoRecord] = {}
    seen_fp: dict[str, VideoRecord] = {}
    kept: list[VideoRecord] = []
    collisions_by_key: dict[str, int] = defaultdict(int)
    collision_matrix: dict[str, int] = defaultdict(int)
    per_source_unique: dict[str, int] = defaultdict(int)

    for rec in items:
        media_key = canonical_url(str(rec.media_url) if rec.media_url else None)
        url_key = canonical_url(str(rec.url) if rec.url else None)
        fp_key = content_fingerprint(rec)

        collided_with: VideoRecord | None = None
        matched_key = ""
        if media_key and media_key in seen_media:
            collided_with = seen_media[media_key]
            matched_key = "media_url"
        elif url_key and url_key in seen_url:
            collided_with = seen_url[url_key]
            matched_key = "url"
        elif fp_key and fp_key in seen_fp:
            collided_with = seen_fp[fp_key]
            matched_key = "fingerprint"

        if collided_with is not None:
            collisions_by_key[matched_key] += 1
            collision_matrix[_pair_key(collided_with.source, rec.source)] += 1
            continue

        if media_key:
            seen_media[media_key] = rec
        if url_key:
            seen_url[url_key] = rec
        if fp_key:
            seen_fp[fp_key] = rec
        kept.append(rec)
        per_source_unique[rec.source] += 1

    report = DedupReport(
        n_input=len(items),
        n_unique=len(kept),
        n_collisions=len(items) - len(kept),
        collisions_by_key=dict(collisions_by_key),
        collision_matrix=dict(collision_matrix),
        per_source_unique=dict(per_source_unique),
    )
    return kept, report
