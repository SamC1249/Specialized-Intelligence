"""Cheap, deterministic, metadata-only dedup.

Two-tier design that is intentionally *not* video-hash. Video-hash is a
future stage that only runs for records we downloaded; this module runs
before we spend any bytes.

Tier 1 (exact): `canonical_url` collapses trailing slashes, tracking
params, host case, and the two YouTube URL forms (`watch?v=` vs
`youtu.be/`). Two records with the same canonical URL are the same
record.

Tier 2 (near-exact): character-shingle Jaccard on the normalized title.
Used only when Tier 1 misses, so a threshold of ~0.85 is safe.

We never mutate records; `merge_records` returns a new list where each
merged group is represented by its highest-quality representative, with
`.provenance.query` extended to record which source ids collapsed into
it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

if TYPE_CHECKING:
    from specint.records import VideoRecord

_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "referrer",
    "spm",
    "share",
    "si",
    "feature",
}
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def canonical_url(url: str) -> str:
    """Normalize a URL for exact-dedup comparisons.

    - lowercase scheme and host
    - strip default ports (80/443)
    - drop tracking query params, sort remaining
    - remove trailing slash on path (except root)
    - map `youtu.be/<id>` <-> `youtube.com/watch?v=<id>`
    """
    if not url:
        return ""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port and ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = host
    elif port:
        netloc = f"{host}:{port}"
    else:
        netloc = host
    path = parsed.path or "/"

    if host in {"youtu.be", "www.youtu.be"} and len(path) > 1:
        vid = path.strip("/").split("/", 1)[0]
        return canonical_url(f"https://www.youtube.com/watch?v={vid}")
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"} and path in {
        "/watch",
        "/shorts",
    }:
        params = dict(parse_qsl(parsed.query, keep_blank_values=False))
        vid = params.get("v") or params.get("videoId")
        if vid:
            netloc = "www.youtube.com"
            path = "/watch"
            parsed = parsed._replace(query=urlencode({"v": vid}))
            return urlunparse((scheme, netloc, path, "", parsed.query, ""))

    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS
    ]
    kept.sort()
    query = urlencode(kept)
    return urlunparse((scheme, netloc, path, "", query, ""))


def _normalize_title(title: str) -> str:
    return " ".join(_WORD_RE.findall(title.lower()))


def title_shingles(title: str, k: int = 5) -> set[str]:
    """Character k-shingles over the normalized title."""
    norm = _normalize_title(title)
    if len(norm) < k:
        return {norm} if norm else set()
    return {norm[i : i + k] for i in range(len(norm) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _score(record: VideoRecord) -> float:
    q = record.quality_score
    if q is not None:
        return float(q)
    return 1.0 if record.license.is_redistributable else 0.0


def merge_records(
    records: Iterable[VideoRecord],
    threshold: float = 0.85,
    shingle_k: int = 5,
) -> list[VideoRecord]:
    """Collapse cross-source duplicates.

    Order of operations:
    1. Group by `canonical_url` (Tier 1). Every group whose size > 1 is
       merged unconditionally.
    2. Remaining singletons are compared pairwise by title Jaccard and
       merged when the score exceeds `threshold`. This is O(n^2) but n
       here is per-query batches (typically << 10^4).
    3. Winner of each group is the highest-quality record; its
       `provenance.query` is extended with `merged=<ids>` so downstream
       consumers can audit the collapse.
    """
    from specint.records import Provenance  # local import to avoid cycles

    items = list(records)
    if len(items) <= 1:
        return items

    canon_groups: dict[str, list[VideoRecord]] = {}
    fallback: list[VideoRecord] = []
    for r in items:
        cu = canonical_url(str(r.url))
        if not cu:
            fallback.append(r)
            continue
        canon_groups.setdefault(cu, []).append(r)

    groups: list[list[VideoRecord]] = []
    singletons: list[VideoRecord] = []
    for members in canon_groups.values():
        if len(members) > 1:
            groups.append(members)
        else:
            singletons.append(members[0])
    singletons.extend(fallback)

    remaining: list[VideoRecord] = list(singletons)
    while remaining:
        head = remaining.pop(0)
        head_shingles = title_shingles(head.title, k=shingle_k)
        cluster = [head]
        still: list[VideoRecord] = []
        for other in remaining:
            other_sh = title_shingles(other.title, k=shingle_k)
            if head.source == other.source:
                still.append(other)
                continue
            if jaccard(head_shingles, other_sh) >= threshold:
                cluster.append(other)
            else:
                still.append(other)
        remaining = still
        groups.append(cluster)

    out: list[VideoRecord] = []
    for group in groups:
        if len(group) == 1:
            out.append(group[0])
            continue
        winner = max(group, key=_score)
        merged_ids = sorted({r.id for r in group if r.id != winner.id})
        new_query = winner.provenance.query
        if merged_ids:
            new_query = f"{new_query}|merged={','.join(merged_ids)}"
        new_prov = Provenance(
            extractor=winner.provenance.extractor,
            extractor_git=winner.provenance.extractor_git,
            fetched_at=winner.provenance.fetched_at,
            query=new_query,
            raw_sha256=winner.provenance.raw_sha256,
            rights=winner.provenance.rights,
        )
        out.append(winner.model_copy(update={"provenance": new_prov}))
    out.sort(key=lambda r: r.id)
    return out


def dedupe_summary(
    records: Iterable[VideoRecord],
    threshold: float = 0.85,
) -> tuple[list[VideoRecord], dict[str, int]]:
    """Return `(merged_records, stats)`.

    Stats include `n_input`, `n_output`, `n_dupes_collapsed`, and
    `n_pairs_by_canonical_url` (Tier-1 hits only).
    """
    items = list(records)
    n_in = len(items)
    canon_hits = 0
    seen: dict[str, int] = {}
    for r in items:
        cu = canonical_url(str(r.url))
        seen[cu] = seen.get(cu, 0) + 1
    for count in seen.values():
        if count > 1:
            canon_hits += count - 1
    merged = merge_records(items, threshold=threshold)
    return merged, {
        "n_input": n_in,
        "n_output": len(merged),
        "n_dupes_collapsed": n_in - len(merged),
        "n_pairs_by_canonical_url": canon_hits,
    }
