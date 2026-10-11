"""Metadata-only cross-source deduplication.

Purpose:
    Collapse records that almost-certainly point at the same underlying
    upload mirrored across sources (e.g. a Wikimedia Commons video also
    indexed by Openverse, or an Internet Archive mirror of a PeerTube
    original). We do this *without* downloading media: the signal we
    use is the metadata we already have.

Algorithm:
    1. For every record, compute a `fingerprint`:
         (normalised_title, duration_bucket_s, author_or_source)
       - normalised_title: lowercase, Unicode-NFKC, punctuation+whitespace
         collapsed to single ASCII spaces, stop-leading-articles stripped.
       - duration_bucket_s: duration rounded to `bucket_s` seconds
         (default 10). Treats `None` as its own bucket so unknown-length
         records never merge with timed ones.
       - author_or_source: lowercased author if present, else the source
         slug.
    2. Records sharing a fingerprint merge into a single `VideoRecord`.
       The chosen representative is the one with the strongest license
       tier (see `LICENSE_RANK`). Ties break on longer description, then
       higher resolution, then lexicographically on `id` for determinism.
    3. The surviving record's `keywords` are the union across the group;
       `recipe_steps` are kept from the representative (steps are
       source-shaped and don't merge safely).

Design notes:
    - Pure function. No I/O, no mutation of inputs.
    - The merge policy preferring the stronger license is deliberate:
      an incorrect merge **reduces** downstream yield rather than
      contaminating a clean record with a permissive one.
    - Extension point: `fingerprint_fn` is pluggable so a future PR can
      slot in a perceptual-hash digest without rewriting the merge
      logic.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable

from specint.records import License, VideoRecord

LICENSE_RANK: dict[License, int] = {
    License.CC0: 6,
    License.PUBLIC_DOMAIN: 5,
    License.CC_BY: 4,
    License.CC_BY_SA: 3,
    License.OTHER_FREE: 2,
    License.UNKNOWN: 1,
    License.RESTRICTED: 0,
}

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_WS_RE = re.compile(r"\s+")
_LEADING_ARTICLES = ("the ", "a ", "an ", "la ", "le ", "les ", "el ", "los ")

Fingerprint = tuple[str, str, str]


def normalise_title(title: str) -> str:
    if not title:
        return ""
    normalised = unicodedata.normalize("NFKC", title).casefold()
    normalised = _PUNCT_RE.sub(" ", normalised)
    normalised = _WS_RE.sub(" ", normalised).strip()
    for article in _LEADING_ARTICLES:
        if normalised.startswith(article):
            normalised = normalised[len(article) :]
            break
    return normalised


def _duration_bucket(duration_s: float | None, bucket_s: int) -> str:
    if duration_s is None or duration_s <= 0:
        return "unknown"
    if bucket_s <= 0:
        return f"{duration_s:.3f}"
    bucket = round(duration_s / bucket_s) * bucket_s
    return f"{bucket}"


def default_fingerprint(record: VideoRecord, bucket_s: int = 10) -> Fingerprint:
    title_key = normalise_title(record.title)
    duration_key = _duration_bucket(record.duration_s, bucket_s)
    author_key = (record.author or record.source or "").casefold().strip()
    return (title_key, duration_key, author_key)


def _rank(record: VideoRecord) -> tuple[int, int, int, str]:
    """Sort key used to pick the merge representative."""
    license_rank = LICENSE_RANK.get(record.license, 0)
    desc_len = len(record.description or "")
    height = record.height or 0
    return (license_rank, desc_len, height, record.id)


def dedupe(
    records: Iterable[VideoRecord],
    *,
    bucket_s: int = 10,
    fingerprint_fn: Callable[[VideoRecord], Fingerprint] | None = None,
) -> list[VideoRecord]:
    """Collapse near-duplicate records; return deterministic representatives."""
    fn = fingerprint_fn or (lambda r: default_fingerprint(r, bucket_s))
    groups: dict[Fingerprint, list[VideoRecord]] = {}
    for record in records:
        groups.setdefault(fn(record), []).append(record)

    merged: list[VideoRecord] = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        rep = max(group, key=_rank)
        keywords: list[str] = []
        seen: set[str] = set()
        for r in group:
            for kw in r.keywords:
                k = kw.strip()
                if k and k.lower() not in seen:
                    keywords.append(k)
                    seen.add(k.lower())
        merged.append(rep.model_copy(update={"keywords": keywords}))

    merged.sort(key=lambda r: r.id)
    return merged


def dedupe_stats(before: list[VideoRecord], after: list[VideoRecord]) -> dict[str, int]:
    """Report counts suitable for inclusion in BenchmarkResult.notes."""
    return {
        "before": len(before),
        "after": len(after),
        "removed": max(0, len(before) - len(after)),
    }
