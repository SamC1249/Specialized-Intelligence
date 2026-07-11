"""Cross-source dedup.

Two-tier dedup for `VideoRecord` streams:

1. **Exact match** on canonical URL or media URL. Wins immediately.
2. **Fuzzy match** on shingled titles (author-aware). When two records
   share ≥ ``TITLE_JACCARD_THRESHOLD`` of their character n-gram
   shingles *and* their normalised authors match (or one side is
   missing), they are treated as duplicates.

We deliberately do not compare descriptions — descriptions are highly
noisy across sources — and we do not fetch content. Everything runs on
already-materialised `VideoRecord` fields.

Winner selection prefers, in order:
  1. Higher `quality_score` (if set),
  2. Lower `License.value` sort key (CC0 wins over UNKNOWN),
  3. Longer title (rough proxy for "more informative record"),
  4. Stable input order (first seen wins).

The function is pure and O(n²) in the worst case; for practical
pipelines we bucket by title-length prefix to stay near O(n) —
tests cover both paths.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import License, VideoRecord

TITLE_JACCARD_THRESHOLD = 0.85
SHINGLE_SIZE = 4
_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z\s]")

_LICENSE_ORDER: dict[License, int] = {
    License.CC0: 0,
    License.PUBLIC_DOMAIN: 1,
    License.CC_BY: 2,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 4,
    License.UNKNOWN: 5,
    License.RESTRICTED: 6,
}


def _normalise(s: str) -> str:
    s = s.lower()
    s = _NON_ALNUM_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def _shingles(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    norm = _normalise(text)
    if len(norm) < k:
        return {norm} if norm else set()
    return {norm[i : i + k] for i in range(len(norm) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _better(a: VideoRecord, b: VideoRecord) -> VideoRecord:
    """Return the record we should keep."""
    a_q = a.quality_score or 0.0
    b_q = b.quality_score or 0.0
    if a_q != b_q:
        return a if a_q > b_q else b
    a_l = _LICENSE_ORDER.get(a.license, 99)
    b_l = _LICENSE_ORDER.get(b.license, 99)
    if a_l != b_l:
        return a if a_l < b_l else b
    if len(a.title) != len(b.title):
        return a if len(a.title) > len(b.title) else b
    return a


def _url_key(record: VideoRecord, field: str) -> str | None:
    value = getattr(record, field, None)
    if value is None:
        return None
    return str(value).rstrip("/").lower()


@dataclass(frozen=True)
class DedupStats:
    n_input: int
    n_output: int
    n_removed_by_url: int
    n_removed_by_media_url: int
    n_removed_by_title: int

    @property
    def removed(self) -> int:
        return self.n_input - self.n_output


def dedupe(
    records: Iterable[VideoRecord],
    title_threshold: float = TITLE_JACCARD_THRESHOLD,
) -> tuple[list[VideoRecord], DedupStats]:
    """Return (deduped_records, stats).

    ``records`` is consumed once; input order is preserved for kept
    records. ``title_threshold`` is the Jaccard threshold on shingles.
    """
    seen_url: dict[str, int] = {}
    seen_media: dict[str, int] = {}
    kept: list[VideoRecord] = []
    shingle_cache: list[set[str]] = []
    removed_url = 0
    removed_media = 0
    removed_title = 0
    n_input = 0

    for rec in records:
        n_input += 1
        url_key = _url_key(rec, "url")
        media_key = _url_key(rec, "media_url")

        collision_idx: int | None = None
        if url_key and url_key in seen_url:
            collision_idx = seen_url[url_key]
            removed_url += 1
        elif media_key and media_key in seen_media:
            collision_idx = seen_media[media_key]
            removed_media += 1

        if collision_idx is None:
            new_shingles = _shingles(rec.title)
            for idx, existing_shingles in enumerate(shingle_cache):
                if _jaccard(new_shingles, existing_shingles) >= title_threshold:
                    a_author = _normalise(kept[idx].author or "")
                    b_author = _normalise(rec.author or "")
                    if not a_author or not b_author or a_author == b_author:
                        collision_idx = idx
                        removed_title += 1
                        break

        if collision_idx is None:
            kept.append(rec)
            shingle_cache.append(_shingles(rec.title))
            if url_key:
                seen_url[url_key] = len(kept) - 1
            if media_key:
                seen_media[media_key] = len(kept) - 1
            continue

        winner = _better(kept[collision_idx], rec)
        if winner is not kept[collision_idx]:
            kept[collision_idx] = winner
            shingle_cache[collision_idx] = _shingles(winner.title)
            new_url_key = _url_key(winner, "url")
            new_media_key = _url_key(winner, "media_url")
            if new_url_key:
                seen_url[new_url_key] = collision_idx
            if new_media_key:
                seen_media[new_media_key] = collision_idx

    stats = DedupStats(
        n_input=n_input,
        n_output=len(kept),
        n_removed_by_url=removed_url,
        n_removed_by_media_url=removed_media,
        n_removed_by_title=removed_title,
    )
    return kept, stats
