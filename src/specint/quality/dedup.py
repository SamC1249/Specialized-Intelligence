"""Metadata-only near-duplicate detection primitives (L1 + L2).

Design rationale is in `docs/artifacts/2026-09-16-video-dedup.md`. L3
(pHash / SSCD over frames) is out of scope until we start downloading
media. L1 and L2 are pure functions so they are trivially testable and
cheap enough to run on every record at ingest.

L1 — canonical URL: strip tracking params, rewrite well-known aliases
(youtu.be, Wikimedia FilePath).

L2 — metadata bucket key: a stable tuple that collides on plausible
near-duplicates (same duration bucket, same resolution class, same
author, same title shingle).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from specint.records import VideoRecord

_TRACKING_PARAMS = re.compile(
    r"^(utm_|fbclid$|gclid$|feature$|si$|_ga$|mc_[cs]id$|ref$|source$)",
    re.IGNORECASE,
)

_HOST_ALIASES: dict[str, str] = {
    "youtu.be": "www.youtube.com",
    "m.youtube.com": "www.youtube.com",
    "www.youtu.be": "www.youtube.com",
    "commons.m.wikimedia.org": "commons.wikimedia.org",
    "en.m.wikipedia.org": "en.wikipedia.org",
}


_YT_SHORT_HOSTS = {"youtu.be", "www.youtu.be", "m.youtu.be"}


def _rewrite_youtube_short(host: str, path: str, query: str) -> tuple[str, str, str]:
    if host in _YT_SHORT_HOSTS and path and path != "/":
        video_id = path.lstrip("/").split("/", 1)[0]
        return "www.youtube.com", "/watch", urlencode({"v": video_id})
    return host, path, query


def _rewrite_commons_filepath(host: str, path: str) -> tuple[str, str]:
    m = re.match(r"^/wiki/Special:FilePath/(.+)$", path)
    if host == "commons.wikimedia.org" and m:
        return host, f"/wiki/File:{m.group(1)}"
    return host, path


def canonical_url(url: str) -> str:
    """Return a canonical form of `url` for L1 dedup.

    Idempotent: `canonical_url(canonical_url(x)) == canonical_url(x)`.
    """
    if not url:
        return ""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    path = parts.path or "/"
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not _TRACKING_PARAMS.match(k)
    ]
    query_pairs.sort()
    query = urlencode(query_pairs)

    host, path, query = _rewrite_youtube_short(host, path, query)
    host = _HOST_ALIASES.get(host, host)
    host, path = _rewrite_commons_filepath(host, path)

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Canonicalise scheme to https for dedup — nearly all live hosts serve
    # both, and treating http/https as distinct URLs guarantees false negatives.
    return urlunsplit(("https", host, path, query, ""))


_TITLE_NOISE = re.compile(r"[^a-z0-9]+")


def _title_shingle(title: str, k: int = 5) -> str:
    """Cheap min-hash-ish signature: sorted set of k-grams of normalized title."""
    norm = _TITLE_NOISE.sub(" ", (title or "").lower()).strip()
    if not norm:
        return ""
    tokens = norm.split()
    if len(tokens) <= k:
        return " ".join(tokens)
    grams = sorted({" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)})
    digest = hashlib.blake2b(" | ".join(grams).encode("utf-8"), digest_size=8).hexdigest()
    return digest


def _duration_bucket(duration_s: float | None, width_s: float = 5.0) -> int:
    if not duration_s or duration_s <= 0:
        return -1
    return round(duration_s / width_s)


def _resolution_class(height: int | None) -> str:
    if height is None or height <= 0:
        return "unknown"
    if height < 480:
        return "<480"
    if height < 720:
        return "480-719"
    if height < 1080:
        return "720-1079"
    return ">=1080"


def bucket_key(record: VideoRecord) -> tuple[int, str, str, str]:
    """L2 metadata bucket key. Two records with the same key are candidates."""
    return (
        _duration_bucket(record.duration_s),
        _resolution_class(record.height),
        (record.author or "").strip().lower(),
        _title_shingle(record.title),
    )


def dedup(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    """Return records with L1+L2 duplicates removed.

    Preference order when collapsing a duplicate set:
      1. license.is_redistributable
      2. highest quality_score (None treated as -1)
      3. earliest published_at
      4. stable by original iteration order

    Pure function: does not mutate input; deterministic on identical
    inputs.
    """
    items = list(records)
    seen_url: dict[str, VideoRecord] = {}
    url_order: list[str] = []
    for r in items:
        ukey = canonical_url(str(r.url))
        if ukey not in seen_url:
            seen_url[ukey] = r
            url_order.append(ukey)
        elif _prefers(r, seen_url[ukey]):
            seen_url[ukey] = r
    l1_pass = [seen_url[k] for k in url_order]

    seen_bucket: dict[tuple[int, str, str, str], VideoRecord] = {}
    bucket_order: list[tuple[int, str, str, str]] = []
    unbucketed: list[VideoRecord] = []
    for r in l1_pass:
        bkey = bucket_key(r)
        if bkey[0] == -1 or not bkey[3]:
            unbucketed.append(r)
            continue
        if bkey not in seen_bucket:
            seen_bucket[bkey] = r
            bucket_order.append(bkey)
        elif _prefers(r, seen_bucket[bkey]):
            seen_bucket[bkey] = r
    return unbucketed + [seen_bucket[k] for k in bucket_order]


def _prefers(new: VideoRecord, old: VideoRecord) -> bool:
    def key(r: VideoRecord) -> tuple[int, float, float]:
        return (
            1 if r.license.is_redistributable else 0,
            r.quality_score if r.quality_score is not None else -1.0,
            -(r.published_at.timestamp() if r.published_at else 0.0),
        )

    return key(new) > key(old)
