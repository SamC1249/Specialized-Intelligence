"""Eval-set deduplication blocklist.

Implements step 3 of the DataComp recipe adapted to video
(see `docs/artifacts/datacomp-filtering-for-video.md`).

A blocklist is a set of 64-bit DCT pHashes (16-char lowercase hex strings)
representing keyframes of *held-out evaluation videos*. Candidate clips
within a configurable Hamming distance are excluded from training
shards.

Public API
----------

- `load_blocklist(path: Path) -> list[str]`
    Read a `.jsonl` file with rows `{"phash64": "...", "source": "..."}`
    and return the deduplicated list of pHash strings.

- `BlockList(phashes: Iterable[str], threshold: int)`
    Wraps a list of pHashes and offers `contains(phash)` and
    `nearest(phash)` queries.

Inputs / outputs are spelled out per-function below. All distances are
*Hamming bit-distance* on 64-bit hashes, range 0..64.

Side effects: none (pure module).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from components.phash import hamming

_HEX64 = 16  # 64-bit hash == 16 hex chars


def _validate_phash(p: str) -> None:
    if not isinstance(p, str) or len(p) != _HEX64:
        raise ValueError(f"phash must be {_HEX64}-char hex string, got: {p!r}")
    try:
        int(p, 16)
    except ValueError as e:
        raise ValueError(f"phash must be hex, got: {p!r}") from e


def load_blocklist(path: Path) -> list[str]:
    """Load a JSON-Lines blocklist file.

    Inputs:
      path: filesystem path to a `.jsonl` file. Each line is a JSON
            object with at minimum `{"phash64": "<16-hex-chars>"}`.
            Other fields (e.g. `"source"`, `"video_id"`) are ignored.

    Outputs:
      list[str]: deduplicated list of 16-char lowercase hex pHashes,
      in insertion order.

    Raises:
      ValueError on malformed rows or non-hex pHashes.
      FileNotFoundError if `path` does not exist.
    """
    seen: set[str] = set()
    out: list[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: invalid JSON") from e
            if "phash64" not in obj:
                raise ValueError(f"{path}:{lineno}: missing 'phash64'")
            p = obj["phash64"].lower()
            _validate_phash(p)
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


@dataclass(frozen=True)
class BlockHit:
    """A single near-duplicate match against the blocklist."""

    phash: str
    distance: int


class BlockList:
    """A pHash blocklist with Hamming-threshold containment query.

    Inputs:
      phashes:   iterable of 16-char lowercase hex pHash strings.
      threshold: maximum Hamming distance (inclusive) to call a match.
                 Range: 0..64. Default 8 (≈12.5% bit difference)
                 mirrors the V-JEPA-2 / DataComp near-duplicate threshold.

    Outputs:
      .contains(phash) -> bool
      .nearest(phash)  -> BlockHit | None  (lowest-distance match)
    """

    def __init__(self, phashes: Iterable[str], threshold: int = 8) -> None:
        if not 0 <= threshold <= 64:
            raise ValueError("threshold must be in [0, 64]")
        self._phashes: list[str] = []
        for p in phashes:
            _validate_phash(p)
            self._phashes.append(p.lower())
        self._threshold = threshold

    @property
    def threshold(self) -> int:
        return self._threshold

    def __len__(self) -> int:
        return len(self._phashes)

    def contains(self, phash: str) -> bool:
        _validate_phash(phash)
        target = phash.lower()
        return any(hamming(target, p) <= self._threshold for p in self._phashes)

    def nearest(self, phash: str) -> BlockHit | None:
        _validate_phash(phash)
        target = phash.lower()
        best: BlockHit | None = None
        for p in self._phashes:
            d = hamming(target, p)
            if d <= self._threshold and (best is None or d < best.distance):
                best = BlockHit(phash=p, distance=d)
        return best


def apply(clips: list[dict], blocklist: BlockList) -> list[dict]:
    """Mark clips that hit the blocklist as excluded.

    Inputs:
      clips: list of clip dicts conforming to CLIP_SCHEMA. Each must have
             a `phash64` field (16-hex string) or this raises ValueError.
      blocklist: a BlockList.

    Outputs:
      list[dict]: copies of input clips, with `excluded=True` and
      `exclusion_reason="eval_blocklist_hit (d=<n>, ref=<phash>)"`
      where the blocklist matched.

    Side effects: none (returns new list, does not mutate inputs).
    """
    out: list[dict] = []
    for clip in clips:
        c = dict(clip)
        ph = c.get("phash64")
        if ph is None:
            raise ValueError(f"clip {c.get('clip_id', '?')} has no phash64")
        hit = blocklist.nearest(ph)
        if hit is not None:
            c["excluded"] = True
            c["exclusion_reason"] = f"eval_blocklist_hit (d={hit.distance}, ref={hit.phash})"
        out.append(c)
    return out
