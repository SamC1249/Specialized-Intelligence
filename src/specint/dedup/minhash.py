"""Deterministic MinHash-lite near-duplicate detection over metadata.

Signature construction:
  1. Normalise the input text (lowercase, strip non-alphanumerics,
     collapse whitespace).
  2. Extract character n-gram shingles (default n=5). This is
     robust to token order and to small typographic differences.
  3. Hash each shingle with a stable 64-bit blake2b, and for each of
     `NUM_PERM` seeded hash functions, keep the minimum. The resulting
     tuple of length NUM_PERM is the signature.

Similarity between two records is the Jaccard estimate:
  |{i : sig_a[i] == sig_b[i]}| / NUM_PERM

We collapse pairs with similarity ≥ JACCARD_THRESHOLD. Canonicalisation
order (pick the survivor):
  1. Higher license tier (redistributable > UNKNOWN > RESTRICTED).
  2. Higher resolution (max(width or 0, height or 0)).
  3. Earlier `published_at` (older is more likely canonical original).
  4. Lexicographically smaller `id` (tie-breaker).

We do *not* do LSH bucketing yet — for N ≤ 10^4 the naive O(N^2)
comparison is faster than the overhead of building buckets. When the
harness graduates past that scale, wrap this in an LSH driver.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from specint.records import License, VideoRecord

NUM_PERM = 32
SHINGLE_SIZE = 5
JACCARD_THRESHOLD = 0.7

_NORMALIZE_RE = re.compile(r"[^0-9a-z\s]+")
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    lowered = text.lower()
    cleaned = _NORMALIZE_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", cleaned).strip()


def _shingles(text: str, n: int = SHINGLE_SIZE) -> list[str]:
    normalized = _normalize(text)
    if len(normalized) < n:
        return [normalized] if normalized else []
    return [normalized[i : i + n] for i in range(len(normalized) - n + 1)]


def _hash(shingle: str, seed: int) -> int:
    h = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8, person=seed.to_bytes(8, "big"))
    return int.from_bytes(h.digest(), "big")


def minhash_signature(text: str, num_perm: int = NUM_PERM) -> tuple[int, ...]:
    shingles = _shingles(text)
    if not shingles:
        return tuple([0] * num_perm)
    sig: list[int] = []
    for seed in range(num_perm):
        best = min(_hash(s, seed) for s in shingles)
        sig.append(best)
    return tuple(sig)


def _record_text(r: VideoRecord) -> str:
    desc = r.description[:200] if r.description else ""
    return f"{r.title} {desc}"


def _jaccard(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    same = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    return same / len(a)


_LICENSE_TIER: dict[License, int] = {
    License.CC0: 5,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 4,
    License.OTHER_FREE: 3,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}


def _resolution(r: VideoRecord) -> int:
    return max(r.width or 0, r.height or 0)


def _rank(r: VideoRecord) -> tuple[int, int, datetime, str]:
    return (
        -_LICENSE_TIER.get(r.license, 0),
        -_resolution(r),
        r.published_at or datetime.max,
        r.id,
    )


def _canonical(records: list[VideoRecord]) -> VideoRecord:
    return sorted(records, key=_rank)[0]


@dataclass(frozen=True)
class DedupResult:
    """Return type of `dedup_records`.

    Attributes:
        kept: canonical survivors, order-preserving with input.
        collapsed_groups: list of lists — one per collision group of 2+
            records; the *first* element is the survivor.
    """

    kept: list[VideoRecord] = field(default_factory=list)
    collapsed_groups: list[list[VideoRecord]] = field(default_factory=list)

    @property
    def n_duplicates_removed(self) -> int:
        return sum(len(g) - 1 for g in self.collapsed_groups)


def dedup_records(
    records: list[VideoRecord],
    threshold: float = JACCARD_THRESHOLD,
) -> DedupResult:
    if not records:
        return DedupResult(kept=[], collapsed_groups=[])

    n = len(records)
    signatures = [minhash_signature(_record_text(r)) for r in records]

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if _jaccard(signatures[i], signatures[j]) >= threshold:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        clusters.setdefault(find(idx), []).append(idx)

    kept: list[VideoRecord] = []
    kept_ids: set[str] = set()
    collapsed: list[list[VideoRecord]] = []
    original_index: dict[str, int] = {r.id: i for i, r in enumerate(records)}

    for members in clusters.values():
        group = [records[i] for i in members]
        winner = _canonical(group)
        if len(group) > 1:
            ordered = [winner] + [r for r in group if r.id != winner.id]
            collapsed.append(ordered)
        kept.append(winner)
        kept_ids.add(winner.id)

    kept.sort(key=lambda r: original_index[r.id])
    return DedupResult(kept=kept, collapsed_groups=collapsed)
