"""Cross-source record deduplication.

Two adapters may return records that point at the *same underlying
video* — most commonly Blender Foundation shorts (PeerTube ⇄ Commons)
or USDA/NIH clips (Archive.org ⇄ Commons). Without dedup, `n_records`
and `unique_authors` in `BenchmarkResult` double-count.

Canonical dedup key (in priority order):
  1. `media_url` normalised (scheme lower, host lower, no trailing "/").
  2. `(source, source_native_id)` — always unique within a source.

Any two records that share (1) collapse into the one with the
highest-tier license (per `License._TIER` below), then the higher
`quality_score` (missing scores treated as -inf).
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from specint.records import License, VideoRecord

_TIER: dict[License, int] = {
    License.CC0: 5,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}


def _canonical_media_key(record: VideoRecord) -> str | None:
    if record.media_url is None:
        return None
    parsed = urlparse(str(record.media_url))
    if not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{host}{path}"


def _rank(record: VideoRecord) -> tuple[int, float]:
    return (_TIER.get(record.license, 0), record.quality_score or float("-inf"))


def dedupe_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return one record per canonical media URL, keeping the "best" one."""
    by_key: dict[str, VideoRecord] = {}
    passthrough: list[VideoRecord] = []
    for rec in records:
        key = _canonical_media_key(rec)
        if key is None:
            passthrough.append(rec)
            continue
        existing = by_key.get(key)
        if existing is None or _rank(rec) > _rank(existing):
            by_key[key] = rec
    return [*by_key.values(), *passthrough]
