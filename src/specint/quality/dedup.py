"""Cross-source deduplication of `VideoRecord` streams.

Why this module exists
----------------------
The seed harness treats every record from every source as unique. In
practice the same Wikimedia Commons video routinely surfaces via:
  * `wikimedia` (canonical page + media URL),
  * `common_crawl` (a recipe blog embeds the Commons `.webm`),
  * `archive_org` (a mirror of the Commons file), and
  * (rarely) a `peertube` re-upload.

Reporting yield without deduplication inflates `total_duration_s` and
gives a false sense of coverage. The rule of thumb from the 2026-09-16
adversarial plan (H2): *false-positive dedup > false-negative dedup*.
When in doubt we keep both records.

Dedup key strategy (in priority order):
  1. **Media URL** — normalized (lowercase host, strip query, strip
     trailing slash). If two records share a media URL they are the
     same underlying media, regardless of source.
  2. **Landing URL** — same normalization.
  3. **`(title, duration_bucket)`** — normalized title (lowercased,
     alphanumerics only) plus duration bucketed to nearest 5 seconds.
     Only used when both title *and* duration are known, to avoid
     collapsing "Chicken curry" tutorials with different durations.

When multiple records collide on the same key we keep the one with the
higher `quality_score` (ties → higher `license.is_redistributable` →
lexicographically first `source`). The rest are returned separately so
callers can log/inspect them.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from specint.records import License, VideoRecord

_TITLE_STRIP_RE = re.compile(r"[^0-9a-z]+")


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(str(url))
    except ValueError:
        return None
    if not parts.scheme or not parts.netloc:
        return None
    host = parts.netloc.lower()
    path = parts.path.rstrip("/")
    return f"{host}{path}"


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return _TITLE_STRIP_RE.sub("", title.lower())


def _duration_bucket(duration_s: float | None, width_s: float = 5.0) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return round(duration_s / width_s)


def dedup_key(record: VideoRecord) -> str | None:
    media = _normalize_url(str(record.media_url) if record.media_url else None)
    if media:
        return f"media:{media}"
    native = record.source_native_id or ""
    if native.startswith("http://") or native.startswith("https://"):
        native_norm = _normalize_url(native)
        if native_norm:
            return f"media:{native_norm}"
    landing = _normalize_url(str(record.url) if record.url else None)
    if landing:
        return f"landing:{landing}"
    title = _normalize_title(record.title)
    bucket = _duration_bucket(record.duration_s)
    if title and bucket is not None:
        return f"title:{title}:{bucket}"
    return None


def _rank(record: VideoRecord) -> tuple[float, int, str]:
    """Higher tuple wins. Quality first, then redistributable, then source name (reversed)."""
    return (
        record.quality_score or 0.0,
        1 if record.license is not License.UNKNOWN and record.license.is_redistributable else 0,
        # Lexicographically first source wins → negate by returning a value where smaller = better.
        # We do this by using a fixed alphabet-negation trick: sort DESC on tuple, so we
        # want a value that's *larger* for lexicographically *smaller* strings. Easiest:
        # invert via chr(255 - ord). For readability we instead flip at the sort call
        # site, so here we just return the raw source string and callers know to prefer
        # the lexicographically smaller one on ties.
        record.source,
    )


@dataclass(frozen=True)
class DedupResult:
    """Return value of :func:`deduplicate`."""

    kept: list[VideoRecord]
    dropped: list[VideoRecord]
    groups: dict[str, list[str]]  # dedup_key -> list of record.id (kept first)

    @property
    def n_dropped(self) -> int:
        return len(self.dropped)


def deduplicate(records: Iterable[VideoRecord]) -> DedupResult:
    """Deterministically deduplicate a stream of records.

    Records without a resolvable dedup key are always kept.
    """
    seen: dict[str, VideoRecord] = {}
    groups: dict[str, list[str]] = {}
    keyless: list[VideoRecord] = []
    dropped: list[VideoRecord] = []

    ordered = sorted(records, key=lambda r: (r.source, r.id))

    for record in ordered:
        key = dedup_key(record)
        if key is None:
            keyless.append(record)
            continue
        if key not in seen:
            seen[key] = record
            groups[key] = [record.id]
            continue

        incumbent = seen[key]
        incumbent_rank = _rank(incumbent)
        challenger_rank = _rank(record)
        if (
            challenger_rank[0] > incumbent_rank[0]
            or (challenger_rank[0] == incumbent_rank[0] and challenger_rank[1] > incumbent_rank[1])
            or (
                challenger_rank[0] == incumbent_rank[0]
                and challenger_rank[1] == incumbent_rank[1]
                and challenger_rank[2] < incumbent_rank[2]
            )
        ):
            dropped.append(incumbent)
            seen[key] = record
            groups[key].insert(0, record.id)
        else:
            dropped.append(record)
            groups[key].append(record.id)

    kept = keyless + list(seen.values())
    kept.sort(key=lambda r: (r.source, r.id))
    dropped.sort(key=lambda r: (r.source, r.id))
    return DedupResult(kept=kept, dropped=dropped, groups=groups)
