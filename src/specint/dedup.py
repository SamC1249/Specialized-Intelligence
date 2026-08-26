"""Phase-1 cross-source deduplication.

W6 in ``docs/plan-2026-08-25.md``: the same clip lives on Wikimedia,
several PeerTube instances, and Internet Archive, so the aggregate
``n_records`` triple-counts it. This module supplies two cheap,
metadata-only signals that we can compute *before* pulling media:

1. A **fingerprint hash** over ``(normalized_title, floor(duration_s),
   normalized_author)``. Two records with the same fingerprint are
   assumed duplicates.
2. **Title-shingle Jaccard** over 3-word shingles. When two records
   share a fingerprint field but not all three, the Jaccard above a
   threshold (default ``0.85``) is a secondary catch for tiny title
   variants ("Cooking Pasta Carbonara" vs "Cooking Pasta Carbonara HD").

The dedup pass is *deterministic and stable*: we sort candidates by
``quality_score`` DESC then by ``id`` ASC, keep the head of each
group, and drop the tail. Callers get back a ``DedupResult`` with the
kept records and the count removed.

Perceptual video hashing (phase-2) is deliberately out of scope until
we start actually pulling media.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^0-9a-z\s]")


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    nkfd = unicodedata.normalize("NFKD", value)
    ascii_ = nkfd.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_.lower()
    stripped = _PUNCT.sub(" ", lowered)
    return _WS.sub(" ", stripped).strip()


def _duration_bucket(duration_s: float | None, bucket: int = 1) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return int(duration_s // bucket)


def fingerprint(record: VideoRecord) -> str:
    """Stable SHA1 over (norm_title, floor(duration_s), norm_author)."""
    key = "|".join(
        [
            _normalize_text(record.title),
            str(_duration_bucket(record.duration_s)),
            _normalize_text(record.author),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def title_shingles(record: VideoRecord, n: int = 3) -> frozenset[str]:
    tokens = _normalize_text(record.title).split()
    if len(tokens) < n:
        return frozenset(tokens)
    return frozenset(" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass(frozen=True)
class DedupResult:
    kept: list[VideoRecord]
    removed: int

    @property
    def n_kept(self) -> int:
        return len(self.kept)


def _sort_key(rec: VideoRecord) -> tuple[float, str]:
    return (-(rec.quality_score or 0.0), rec.id)


def deduplicate(
    records: Iterable[VideoRecord],
    jaccard_threshold: float = 0.85,
) -> DedupResult:
    """Return a stable, deduplicated view of ``records``.

    Determinism: the order of the input never changes the output. We
    sort by (quality DESC, id ASC) before scanning so the highest-
    quality copy of a duplicate group is the survivor.
    """
    items = sorted(records, key=_sort_key)

    kept: list[VideoRecord] = []
    kept_fps: set[str] = set()
    kept_shingles: list[frozenset[str]] = []
    removed = 0

    for rec in items:
        fp = fingerprint(rec)
        if fp in kept_fps:
            removed += 1
            continue
        sh = title_shingles(rec)
        is_dup = False
        for existing_sh in kept_shingles:
            if jaccard(sh, existing_sh) >= jaccard_threshold:
                is_dup = True
                break
        if is_dup:
            removed += 1
            continue
        kept.append(rec)
        kept_fps.add(fp)
        kept_shingles.append(sh)

    return DedupResult(kept=kept, removed=removed)


__all__ = [
    "DedupResult",
    "deduplicate",
    "fingerprint",
    "jaccard",
    "title_shingles",
]
