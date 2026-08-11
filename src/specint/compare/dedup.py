"""Cross-source deduplication.

The same media asset can appear in multiple registries (a Prelinger clip
mirrored on both `archive_org` and `wikimedia`, a PeerTube instance
mirroring an IA recipe, etc.). We collapse near-duplicates *conservatively*
so downstream training corpora do not over-weight mirrored footage.

Key = (normalized_title_bigrams, duration_bucket)
  - normalized title: lower-case, alnum-only, collapsed whitespace, then
    the first 6 bigrams (order-preserving) are joined. This tolerates
    minor punctuation / capitalization drift across sources.
  - duration bucket: floor(duration_s / 30). ~30-second bucket keeps the
    "same clip, same runtime" invariant tight enough to avoid merging
    genuinely different short clips of similar length.

`dedupe` returns a `DedupResult` (immutable) with:
  - `records`: post-dedup list, sorted by (source, id).
  - `n_input`, `n_output`: raw counters.
  - `cross_source_duplicates`: number of collapsed groups whose members
    came from >= 2 distinct sources.
  - `groups`: parallel list of collapsed source ids per output record;
    lets callers audit which records were merged.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from specint.records import VideoRecord

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = _NON_ALNUM.sub(" ", t)
    t = " ".join(t.split())
    return t


def _title_key(title: str) -> str:
    norm = _normalize_title(title)
    if len(norm) < 3:
        return norm
    bigrams = [norm[i : i + 2] for i in range(len(norm) - 1)][:6]
    return "|".join(bigrams)


def _duration_bucket(duration_s: float | None) -> int:
    if duration_s is None or duration_s <= 0:
        return -1
    return int(duration_s // 30)


def dedup_key(record: VideoRecord) -> tuple[str, int]:
    return (_title_key(record.title), _duration_bucket(record.duration_s))


@dataclass(frozen=True)
class DedupResult:
    records: list[VideoRecord]
    n_input: int
    n_output: int
    cross_source_duplicates: int
    groups: list[list[str]]


def dedupe(records: Iterable[VideoRecord]) -> DedupResult:
    grouped: dict[tuple[str, int], list[VideoRecord]] = {}
    order: list[tuple[str, int]] = []
    items = list(records)
    for r in items:
        key = dedup_key(r)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(r)

    picked: list[VideoRecord] = []
    groups: list[list[str]] = []
    cross_source = 0
    for key in order:
        members = grouped[key]
        winner = _pick_winner(members)
        picked.append(winner)
        groups.append([m.id for m in members])
        sources = {m.source for m in members}
        if len(sources) >= 2:
            cross_source += 1

    picked.sort(key=lambda r: (r.source, r.id))
    return DedupResult(
        records=picked,
        n_input=len(items),
        n_output=len(picked),
        cross_source_duplicates=cross_source,
        groups=groups,
    )


def _pick_winner(members: list[VideoRecord]) -> VideoRecord:
    """Prefer license-clean, then highest quality_score, then longest text."""

    def sort_key(rec: VideoRecord) -> tuple[int, float, int]:
        return (
            1 if rec.license.is_redistributable else 0,
            rec.quality_score if rec.quality_score is not None else 0.0,
            len(rec.title) + len(rec.description),
        )

    return max(members, key=sort_key)
