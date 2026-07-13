"""Cross-source deduplication for `VideoRecord`.

Two videos returned by two different adapters can still be the same
physical asset (Wikimedia mirrors on Internet Archive; recipe blogs
re-embed both). Training corpora that double-count them inflate reported
hours and silently over-weight popular assets.

We use two complementary signals:

  - **Canonical key** — deterministic tuple of
    `(normalised_title, author, duration_bucket)` used to detect exact
    duplicates. Cheap; O(n).
  - **SimHash near-duplicate** — 64-bit SimHash over stopword-stripped
    bigrams of `title + description`. Two records are declared "near
    duplicates" when Hamming distance ≤ `threshold`. The default of
    `3` targets long descriptions where bag-of-bigrams is stable;
    short-title corpora (Commons, PeerTube snippets) benefit from
    `threshold ~ 12-16` because a single word change can flip ~10 bits
    on a 64-bit hash. Callers must tune this per corpus and log the
    value they used in their benchmark notes.

Both functions are pure. The dedup layer never mutates its inputs; it
returns a filtered list plus, if requested, the mapping from kept
records to their absorbed duplicates so provenance can be preserved.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "or",
        "the",
        "of",
        "to",
        "for",
        "with",
        "on",
        "in",
        "at",
        "by",
        "how",
        "make",
        "makes",
        "making",
        "recipe",
        "recipes",
        "cooking",
        "cook",
        "step",
        "steps",
        "video",
        "hd",
        "4k",
        "youtube",
        "part",
        "no",
        "de",
        "la",
        "le",
        "les",
        "el",
        "et",
        "un",
        "una",
    }
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _normalise_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return " ".join(_WORD_RE.findall(text))


def _tokens(text: str) -> list[str]:
    tokens = _normalise_text(text).split()
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _duration_bucket(duration_s: float | None, bucket_s: int = 15) -> int:
    if duration_s is None or duration_s <= 0:
        return 0
    return int(duration_s // bucket_s)


def canonical_key(record: VideoRecord) -> tuple[str, str, int]:
    title = " ".join(_tokens(record.title))[:120]
    author = _normalise_text(record.author or "")
    return (title, author, _duration_bucket(record.duration_s))


def _bigrams(tokens: list[str]) -> list[str]:
    if len(tokens) < 2:
        return list(tokens)
    return [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)]


def _feature_hash(feature: str) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def simhash(text: str, bits: int = 64) -> int:
    tokens = _tokens(text)
    features = _bigrams(tokens) or tokens
    if not features:
        return 0
    vec = [0] * bits
    for f in features:
        h = _feature_hash(f)
        for i in range(bits):
            if h & (1 << i):
                vec[i] += 1
            else:
                vec[i] -= 1
    out = 0
    for i in range(bits):
        if vec[i] > 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@dataclass(frozen=True)
class DedupResult:
    kept: list[VideoRecord]
    absorbed: dict[str, list[str]]

    def n_dropped(self) -> int:
        return sum(len(v) for v in self.absorbed.values())


def _record_text(r: VideoRecord) -> str:
    parts = [r.title or "", r.description or ""]
    parts.extend(r.keywords or [])
    return " ".join(p for p in parts if p)


def pairwise_similar(
    records: Iterable[VideoRecord],
    threshold: int = 3,
) -> list[tuple[str, str, int]]:
    """Return `(id_a, id_b, hamming_distance)` triples for near-duplicates."""
    items = [(r, simhash(_record_text(r))) for r in records]
    out: list[tuple[str, str, int]] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            d = hamming(items[i][1], items[j][1])
            if d <= threshold:
                out.append((items[i][0].id, items[j][0].id, d))
    return out


_LICENSE_RANK = {
    "CC0": 5,
    "PUBLIC_DOMAIN": 4,
    "CC-BY": 3,
    "CC-BY-SA": 2,
    "OTHER_FREE": 1,
    "UNKNOWN": 0,
    "RESTRICTED": -1,
}


def _prefer(a: VideoRecord, b: VideoRecord) -> VideoRecord:
    rank_a = _LICENSE_RANK.get(a.license.value, 0)
    rank_b = _LICENSE_RANK.get(b.license.value, 0)
    if rank_a != rank_b:
        return a if rank_a > rank_b else b
    qa = a.quality_score or 0.0
    qb = b.quality_score or 0.0
    if qa != qb:
        return a if qa > qb else b
    return a if a.id <= b.id else b


def deduplicate(
    records: Iterable[VideoRecord],
    near_threshold: int = 3,
) -> DedupResult:
    """Collapse exact + near duplicates. Deterministic order preserved."""
    items = list(records)
    kept_by_key: dict[tuple[str, str, int], VideoRecord] = {}
    absorbed: dict[str, list[str]] = {}

    exact_pass: list[VideoRecord] = []
    for r in items:
        key = canonical_key(r)
        if key in kept_by_key:
            winner = _prefer(kept_by_key[key], r)
            loser_id = r.id if winner is kept_by_key[key] else kept_by_key[key].id
            absorbed.setdefault(winner.id, []).append(loser_id)
            kept_by_key[key] = winner
        else:
            kept_by_key[key] = r
    for r in kept_by_key.values():
        exact_pass.append(r)

    if near_threshold <= 0:
        return DedupResult(kept=exact_pass, absorbed=absorbed)

    hashed = [(r, simhash(_record_text(r))) for r in exact_pass]
    dropped_ids: set[str] = set()
    kept: list[VideoRecord] = []
    for i, (r_i, h_i) in enumerate(hashed):
        if r_i.id in dropped_ids:
            continue
        winner = r_i
        for j in range(i + 1, len(hashed)):
            r_j, h_j = hashed[j]
            if r_j.id in dropped_ids:
                continue
            if hamming(h_i, h_j) <= near_threshold:
                candidate = _prefer(winner, r_j)
                loser = r_j if candidate is winner else winner
                absorbed.setdefault(candidate.id, []).append(loser.id)
                dropped_ids.add(loser.id)
                winner = candidate
        kept.append(winner)

    seen: set[str] = set()
    unique_kept: list[VideoRecord] = []
    for r in kept:
        if r.id in seen or r.id in dropped_ids:
            continue
        seen.add(r.id)
        unique_kept.append(r)
    return DedupResult(kept=unique_kept, absorbed=absorbed)
