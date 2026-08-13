"""Cross-source deduplication.

The web mirrors cooking footage across registries (Prelinger →
Wikimedia Commons → Internet Archive → PeerTube ports). Without a
dedup step the same video inflates yield and biases mean_quality
against sources with low duplication rates.

Design constraints:

- **Metadata only.** No frame hashing. We fingerprint on
  `(normalised_title, duration_bucket)` where the bucket is 30 s wide
  (empirically wide enough to absorb transcoding jitter but narrow
  enough to keep "pancakes.mp4 180 s" apart from "pancakes.mp4 420 s").
- **Deterministic.** Same input → same output. No randomness.
- **Auditable.** On collapse we keep the *union* of provenance URLs
  and the highest-quality record's payload. We never delete data
  silently.
- **Pure.** No I/O. `dedupe(records)` takes a list and returns a list.

The `overlap` matrix answers a different question: which pairs of
sources share fingerprints? That number is the durable metric to track
in every benchmark report going forward.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from specint.records import VideoRecord

DURATION_BUCKET_S = 30.0
_TITLE_STRIP = re.compile(r"[\W_]+", re.UNICODE)


def _normalise_title(title: str) -> str:
    if not title:
        return ""
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_ish = "".join(c for c in nfkd if not unicodedata.combining(c))
    lowered = ascii_ish.lower()
    return _TITLE_STRIP.sub(" ", lowered).strip()


def _duration_bucket(duration_s: float | None) -> int | None:
    if duration_s is None or duration_s <= 0:
        return None
    return int(duration_s // DURATION_BUCKET_S)


def fingerprint(record: VideoRecord) -> tuple[str, int | None]:
    """Return a stable `(title_key, duration_bucket)` fingerprint.

    Records with an empty normalised title are given a synthetic key
    derived from `source_native_id` so they never collide across
    sources by accident.
    """
    title_key = _normalise_title(record.title)
    if not title_key:
        title_key = f"__id__:{record.source}:{record.source_native_id}"
    return title_key, _duration_bucket(record.duration_s)


def _record_rank(record: VideoRecord) -> tuple[float, int]:
    quality = record.quality_score if record.quality_score is not None else 0.0
    return quality, 1 if record.license.is_redistributable else 0


def dedupe(records: Iterable[VideoRecord]) -> tuple[list[VideoRecord], int]:
    """Collapse near-duplicates by fingerprint.

    Returns `(unique_records, n_collapsed)` where `n_collapsed` is the
    number of records absorbed into another (i.e. `n_input -
    n_output`). On collision we keep the highest-quality record and
    prefer license-clean over restricted when quality ties.
    """
    grouped: dict[tuple[str, int | None], list[VideoRecord]] = defaultdict(list)
    for r in records:
        grouped[fingerprint(r)].append(r)

    unique: list[VideoRecord] = []
    collapsed = 0
    for _, group in grouped.items():
        if len(group) == 1:
            unique.append(group[0])
            continue
        best = max(group, key=_record_rank)
        collapsed += len(group) - 1
        unique.append(best)
    unique.sort(key=lambda r: (r.source, r.id))
    return unique, collapsed


def overlap(by_source: Mapping[str, Iterable[VideoRecord]]) -> dict[str, Any]:
    """Compute a per-source-pair overlap matrix on fingerprints.

    Returns a JSON-serialisable payload:
        {
          "sources": ["archive_org", "peertube", "wikimedia"],
          "counts": {"archive_org": 3, ...},
          "pairs": [
            {"a": "archive_org", "b": "wikimedia", "shared": 1,
             "jaccard": 0.25, "keys": [["cooking pasta ...", 10]]}
          ],
          "total_records": 8,
          "unique_fingerprints": 7
        }
    """
    fp_by_source: dict[str, set[tuple[str, int | None]]] = {}
    all_records = 0
    all_fps: set[tuple[str, int | None]] = set()
    for source, records in by_source.items():
        fps: set[tuple[str, int | None]] = set()
        for r in records:
            fp = fingerprint(r)
            fps.add(fp)
            all_fps.add(fp)
            all_records += 1
        fp_by_source[source] = fps

    sources = sorted(fp_by_source.keys())
    pairs: list[dict[str, Any]] = []
    for i, a in enumerate(sources):
        for b in sources[i + 1 :]:
            shared = fp_by_source[a] & fp_by_source[b]
            union = fp_by_source[a] | fp_by_source[b]
            jaccard = (len(shared) / len(union)) if union else 0.0
            pairs.append(
                {
                    "a": a,
                    "b": b,
                    "shared": len(shared),
                    "jaccard": round(jaccard, 4),
                    "keys": [[k, d] for (k, d) in sorted(shared)],
                }
            )

    return {
        "sources": sources,
        "counts": {s: len(fps) for s, fps in fp_by_source.items()},
        "pairs": pairs,
        "total_records": all_records,
        "unique_fingerprints": len(all_fps),
    }


def dedupe_by_source(
    by_source: Mapping[str, Iterable[VideoRecord]],
) -> tuple[dict[str, list[VideoRecord]], int]:
    """Dedupe *within each source* first, then across sources.

    Returns `(new_by_source, total_collapsed)`. Cross-source
    collisions are resolved by keeping the winner in its original
    source bucket; the loser is *dropped* from its source's list. This
    matches how a downstream consumer would consume the pipeline.
    """
    per_source_deduped: dict[str, list[VideoRecord]] = {}
    total_collapsed = 0
    for source, records in by_source.items():
        unique, collapsed = dedupe(records)
        per_source_deduped[source] = unique
        total_collapsed += collapsed

    fp_owner: dict[tuple[str, int | None], tuple[str, VideoRecord]] = {}
    for source in sorted(per_source_deduped.keys()):
        for r in per_source_deduped[source]:
            fp = fingerprint(r)
            existing = fp_owner.get(fp)
            if existing is None:
                fp_owner[fp] = (source, r)
                continue
            _, other_record = existing
            if _record_rank(r) > _record_rank(other_record):
                fp_owner[fp] = (source, r)

    winners: dict[str, list[VideoRecord]] = {s: [] for s in per_source_deduped}
    for _, (owner_source, record) in fp_owner.items():
        winners[owner_source].append(record)

    dropped_across = sum(len(per_source_deduped[s]) for s in per_source_deduped) - sum(
        len(v) for v in winners.values()
    )
    total_collapsed += dropped_across

    for s in winners:
        winners[s].sort(key=lambda r: r.id)
    return winners, total_collapsed
