"""Metadata-only near-duplicate detection (Phase 1).

Given a batch of `VideoRecord`s, group near-duplicates using three cheap
signals:

  1. Normalized landing-page URL (host + path, no tracking params).
  2. Jaccard similarity on lowercased alphanumeric title tokens.
  3. Coarse duration bucket (default 15s), tolerating a ±1 bucket diff.

Two records are treated as near-duplicates iff their normalized URL is
identical, OR (title-token Jaccard >= `title_jaccard_threshold` AND
duration buckets differ by no more than `duration_bucket_tolerance`).

The output is a `DedupResult` per source with `n_records`, `n_unique`,
`n_duplicates`, and per-duplicate `DuplicateGroup` entries carrying the
`reason` string that made them collapse. Everything is pure and
deterministic: the same input always produces the same grouping, with
records within a group ordered by canonical URL then id.

Design notes:

- Union-find on the similarity graph, so grouping is transitive.
- Zero network I/O; safe for CI.
- Tokenization uses a tiny checked-in English stop-list to avoid
  matching two unrelated recipes solely because they both contain
  "the recipe cooking". Multilingual stop-word support is deliberately
  deferred (see `docs/plan-2026-09-12.md`, H5).

See `docs/artifacts/2026-09-12-video-dedup.md` for the three-phase
plan; this module is Phase 1 only.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from specint.records import VideoRecord

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TRACKING_PARAMS = frozenset(
    {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
)
_ENGLISH_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "your",
        "you",
        "recipe",
        "cooking",
        "video",
    }
)

DEFAULT_TITLE_JACCARD = 0.85
DEFAULT_DURATION_BUCKET_S = 15.0
DEFAULT_BUCKET_TOLERANCE = 1


def normalize_url(url: str | Any) -> str:
    """Return a canonicalized (scheme-less, tracking-clean) URL string.

    Accepts `str`, `pydantic.AnyHttpUrl`, or anything with `__str__`.
    Idempotent; falls back to the raw string on parse errors.
    """
    raw = str(url).strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw.lower()
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    if parsed.query:
        keep: list[str] = []
        for kv in parsed.query.split("&"):
            if not kv:
                continue
            key = kv.split("=", 1)[0].lower()
            if key not in _TRACKING_PARAMS:
                keep.append(kv)
        query = "&".join(sorted(keep))
    else:
        query = ""
    canonical = f"{host}{path}"
    if query:
        canonical = f"{canonical}?{query}"
    return canonical


def title_tokens(title: str) -> frozenset[str]:
    tokens = {tok for tok in _TOKEN_RE.findall(title.lower()) if tok not in _ENGLISH_STOP}
    return frozenset(tokens)


def _duration_bucket(duration_s: float | None, bucket_s: float) -> int | None:
    if duration_s is None or duration_s <= 0 or bucket_s <= 0:
        return None
    return int(duration_s // bucket_s)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


@dataclass(frozen=True)
class DuplicateGroup:
    representative_id: str
    member_ids: tuple[str, ...]
    reason: str

    @property
    def size(self) -> int:
        return len(self.member_ids)

    @property
    def n_extras(self) -> int:
        return max(0, self.size - 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "representative_id": self.representative_id,
            "member_ids": list(self.member_ids),
            "reason": self.reason,
            "size": self.size,
        }


@dataclass(frozen=True)
class DedupResult:
    source: str
    n_records: int
    n_unique: int
    duplicate_groups: tuple[DuplicateGroup, ...] = field(default_factory=tuple)

    @property
    def n_duplicates(self) -> int:
        return sum(g.n_extras for g in self.duplicate_groups)

    @property
    def dup_rate(self) -> float:
        if self.n_records <= 0:
            return 0.0
        return self.n_duplicates / self.n_records

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "n_records": self.n_records,
            "n_unique": self.n_unique,
            "n_duplicates": self.n_duplicates,
            "dup_rate": round(self.dup_rate, 6),
            "duplicate_groups": [g.to_dict() for g in self.duplicate_groups],
        }


class _UnionFind:
    def __init__(self, keys: Iterable[str]) -> None:
        self._parent: dict[str, str] = {k: k for k in keys}

    def find(self, k: str) -> str:
        root = k
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[k] != root:
            self._parent[k], k = root, self._parent[k]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        lo, hi = sorted((ra, rb))
        self._parent[hi] = lo

    def groups(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k in self._parent:
            out.setdefault(self.find(k), []).append(k)
        return out


def dedup_records(
    records: Sequence[VideoRecord],
    source: str,
    *,
    title_jaccard_threshold: float = DEFAULT_TITLE_JACCARD,
    duration_bucket_s: float = DEFAULT_DURATION_BUCKET_S,
    bucket_tolerance: int = DEFAULT_BUCKET_TOLERANCE,
) -> DedupResult:
    """Group `records` (all from `source`) into near-duplicate clusters."""
    if not records:
        return DedupResult(source=source, n_records=0, n_unique=0)

    ids = [r.id for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError(
            f"duplicate VideoRecord.id inside a single source batch for {source!r}; "
            "adapters must produce stable, unique ids per record."
        )

    urls = {r.id: normalize_url(r.url) for r in records}
    titles = {r.id: title_tokens(r.title) for r in records}
    buckets = {r.id: _duration_bucket(r.duration_s, duration_bucket_s) for r in records}

    uf = _UnionFind(ids)
    reasons_by_pair: list[tuple[str, str, str]] = []

    for i, rec_a in enumerate(records):
        a_id = rec_a.id
        for rec_b in records[i + 1 :]:
            b_id = rec_b.id
            if urls[a_id] and urls[a_id] == urls[b_id]:
                reasons_by_pair.append((a_id, b_id, "url"))
                uf.union(a_id, b_id)
                continue
            ba, bb = buckets[a_id], buckets[b_id]
            if ba is None or bb is None:
                continue
            if abs(ba - bb) > bucket_tolerance:
                continue
            if _jaccard(titles[a_id], titles[b_id]) < title_jaccard_threshold:
                continue
            reasons_by_pair.append((a_id, b_id, "title+duration"))
            uf.union(a_id, b_id)

    reasons_by_root: dict[str, set[str]] = {}
    for a_id, _b_id, reason in reasons_by_pair:
        root = uf.find(a_id)
        reasons_by_root.setdefault(root, set()).add(reason)

    _REASON_PRIORITY = ("url", "title+duration")
    by_root = uf.groups()
    urls_by_id = urls
    dup_groups: list[DuplicateGroup] = []
    for root, members in sorted(by_root.items()):
        if len(members) <= 1:
            continue
        ordered = sorted(members, key=lambda mid: (urls_by_id.get(mid, ""), mid))
        found = reasons_by_root.get(root, {"url"})
        reason = next((r for r in _REASON_PRIORITY if r in found), "url")
        dup_groups.append(
            DuplicateGroup(
                representative_id=ordered[0],
                member_ids=tuple(ordered),
                reason=reason,
            )
        )

    return DedupResult(
        source=source,
        n_records=len(records),
        n_unique=len(by_root),
        duplicate_groups=tuple(dup_groups),
    )


def dedup_by_source(
    by_source: dict[str, list[VideoRecord]],
    **kwargs: Any,
) -> dict[str, DedupResult]:
    return {source: dedup_records(recs, source, **kwargs) for source, recs in by_source.items()}


def aggregate_dedup(results: Iterable[DedupResult], name: str = "__total__") -> DedupResult:
    results = list(results)
    n_records = sum(r.n_records for r in results)
    n_unique = sum(r.n_unique for r in results)
    groups: list[DuplicateGroup] = []
    for r in results:
        groups.extend(r.duplicate_groups)
    return DedupResult(
        source=name,
        n_records=n_records,
        n_unique=n_unique,
        duplicate_groups=tuple(groups),
    )
