"""Cross-source deduplication for `VideoRecord`s.

Rationale: the same cooking video is often mirrored across Wikimedia
Commons, Internet Archive, a PeerTube instance, and embedded in a
recipe page indexed by Common Crawl. Counting the same clip four times
inflates yield and biases every downstream benchmark. Dedup is
metadata-only (title + canonical URL + author + duration): it will
collapse mirrors, not identify frame-level near-duplicates.

Two signals:

1. **Canonical URL key.** Strip scheme, `www.`, query string, fragment,
   and common CDN prefixes (`upload.wikimedia.org/wikipedia/commons/`
   → `commons`, `archive.org/download/<id>/...` → `archive/<id>`). If
   two records share the same canonical key, they're the same asset.
2. **Title-shingle Jaccard.** Lowercased title tokens → 3-grams over
   characters. Two records with `>= JACCARD_THRESHOLD` overlap AND
   (same author OR duration within 5%) are considered duplicates.

Both signals are pure functions of metadata, so they run offline on
fixtures. The clustering is deterministic: iterate records in a stable
order and use union-find.

Returned artefact:

* `dedupe(records)` returns a `DedupReport` with:
  - `unique`: canonicalised records (representative per cluster)
  - `duplicates`: records dropped
  - `clusters`: list of lists (each list is a duplicate cluster)
  - `pairs_by_signal`: {"url": n, "title_jaccard": n}
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from specint.records import VideoRecord

JACCARD_THRESHOLD = 0.85
DURATION_TOLERANCE = 0.05
SHINGLE_SIZE = 3

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def canonicalize_url(url: str) -> str:
    """Return a normalized key for a URL.

    Rules (all lowercased, stripped):
      - drop scheme, port, query, fragment
      - drop leading `www.`
      - collapse Wikimedia thumbnail prefixes to their canonical file path
      - drop archive.org `/download/` prefix so `details/<id>` and
        `download/<id>/foo.mp4` collapse to the same key
      - trailing slash stripped
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url.strip().lower()
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or ""

    if host == "upload.wikimedia.org":
        path = re.sub(r"^/wikipedia/[^/]+/thumb/", "/wikipedia/commons/", path)
        path = re.sub(r"^/wikipedia/[^/]+/", "/wikipedia/commons/", path)
    if host == "commons.wikimedia.org":
        path = re.sub(r"^/wiki/File:", "/file/", path, flags=re.IGNORECASE)
    if host == "archive.org":
        path = re.sub(r"^/download/([^/]+)/.*$", r"/details/\1", path)

    path = path.rstrip("/").lower()
    return f"{host}{path}"


def normalize_title(title: str) -> str:
    return " ".join(_TOKEN_RE.findall((title or "").lower()))


def _shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    if not text:
        return set()
    if len(text) < size:
        return {text}
    return {text[i : i + size] for i in range(len(text) - size + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _duration_close(x: float | None, y: float | None) -> bool:
    if x is None or y is None:
        return False
    if x <= 0 or y <= 0:
        return False
    ratio = min(x, y) / max(x, y)
    return (1.0 - ratio) <= DURATION_TOLERANCE


class _DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


@dataclass(frozen=True)
class DedupReport:
    unique: list[VideoRecord] = field(default_factory=list)
    duplicates: list[VideoRecord] = field(default_factory=list)
    clusters: list[list[VideoRecord]] = field(default_factory=list)
    pairs_by_signal: dict[str, int] = field(default_factory=dict)

    @property
    def n_input(self) -> int:
        return sum(len(c) for c in self.clusters)

    @property
    def n_unique(self) -> int:
        return len(self.unique)


def _sort_key(r: VideoRecord) -> tuple[int, str]:
    priority = 0 if r.license.is_redistributable else 1
    return (priority, r.id)


def dedupe(records: Iterable[VideoRecord]) -> DedupReport:
    items = list(records)
    if not items:
        return DedupReport(unique=[], duplicates=[], clusters=[], pairs_by_signal={})

    n = len(items)
    dsu = _DSU(n)
    pairs = {"url": 0, "title_jaccard": 0}

    url_index: dict[str, int] = {}
    for i, r in enumerate(items):
        keys = {canonicalize_url(str(r.url))}
        if r.media_url is not None:
            keys.add(canonicalize_url(str(r.media_url)))
        for k in keys:
            if not k:
                continue
            if k in url_index:
                dsu.union(i, url_index[k])
                pairs["url"] += 1
            else:
                url_index[k] = i

    shingles = [_shingles(normalize_title(r.title)) for r in items]
    for i in range(n):
        for j in range(i + 1, n):
            if dsu.find(i) == dsu.find(j):
                continue
            sim = jaccard(shingles[i], shingles[j])
            if sim < JACCARD_THRESHOLD:
                continue
            a, b = items[i], items[j]
            same_author = bool(
                a.author and b.author and a.author.strip().lower() == b.author.strip().lower()
            )
            if same_author or _duration_close(a.duration_s, b.duration_s):
                dsu.union(i, j)
                pairs["title_jaccard"] += 1

    clusters_by_root: dict[int, list[int]] = {}
    for i in range(n):
        clusters_by_root.setdefault(dsu.find(i), []).append(i)

    clusters: list[list[VideoRecord]] = []
    unique: list[VideoRecord] = []
    duplicates: list[VideoRecord] = []
    for _root, idxs in clusters_by_root.items():
        cluster = sorted((items[i] for i in idxs), key=_sort_key)
        clusters.append(cluster)
        rep = cluster[0]
        unique.append(rep)
        duplicates.extend(cluster[1:])

    unique.sort(key=lambda r: r.id)
    duplicates.sort(key=lambda r: r.id)
    return DedupReport(
        unique=unique,
        duplicates=duplicates,
        clusters=[sorted(c, key=lambda r: r.id) for c in clusters],
        pairs_by_signal=pairs,
    )
