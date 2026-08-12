"""Cross-source deduplication.

Videos often appear on more than one legal host — e.g. Blender's short
films on Commons *and* on `video.blender.org`, or Internet Archive
mirrors of Wikimedia items. Counting each occurrence independently
inflates yield and biases quality against sources with less overlap.

The fingerprint is deliberately conservative:

    (normalized_title, duration_bucket_10s, author_slug)

- `normalized_title`: lower-cased, ASCII-folded, punctuation stripped,
  whitespace collapsed. Titles are the strongest cross-source signal.
- `duration_bucket_10s`: `int(duration_s // 10)` or `-1` when unknown.
  Reduces collisions from unrelated videos with the same short title
  ("Pasta") without over-collapsing near-duplicates.
- `author_slug`: lower-cased author, punctuation stripped; empty
  string when unknown. Two unrelated cooks who both publish "Pasta"
  at similar durations are still preserved.

The module returns:
- `fingerprint(record)`: stable string key,
- `dedupe(records)`: keeps the highest-quality record per fingerprint,
- `overlap(by_source)`: for each unordered pair of sources, count the
  fingerprints present in both. Emits a JSON-serialisable dict for the
  benchmark report.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", text)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    stripped = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", stripped).strip()


def _duration_bucket(duration_s: float | None) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return int(duration_s // 10)


def fingerprint(record: VideoRecord) -> str:
    title = _normalize(record.title)
    author = _normalize(record.author or "")
    bucket = _duration_bucket(record.duration_s)
    return f"{title}|d={bucket}|a={author}"


def dedupe(records: list[VideoRecord]) -> list[VideoRecord]:
    """Return one record per fingerprint, preferring higher quality."""

    best: dict[str, VideoRecord] = {}
    for r in records:
        fp = fingerprint(r)
        prev = best.get(fp)
        if prev is None:
            best[fp] = r
            continue
        prev_q = prev.quality_score or 0.0
        cur_q = r.quality_score or 0.0
        if cur_q > prev_q:
            best[fp] = r
    return list(best.values())


def overlap(by_source: Mapping[str, list[VideoRecord]]) -> dict[str, int]:
    """Return a JSON-safe overlap map keyed by `"src_a__src_b"`.

    Only unordered pairs are emitted, with `src_a < src_b`. The value is
    the count of fingerprints shared between the two sources' records.
    """

    fps_by_source: dict[str, set[str]] = {}
    for source, records in by_source.items():
        fps_by_source[source] = {fingerprint(r) for r in records}
    result: dict[str, int] = {}
    names = sorted(fps_by_source)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = fps_by_source[a] & fps_by_source[b]
            if shared:
                result[f"{a}__{b}"] = len(shared)
    return result


def group_by_fingerprint(records: list[VideoRecord]) -> dict[str, list[VideoRecord]]:
    """Diagnostic helper used by tests and CLI reports."""

    grouped: dict[str, list[VideoRecord]] = defaultdict(list)
    for r in records:
        grouped[fingerprint(r)].append(r)
    return dict(grouped)
