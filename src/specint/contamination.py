"""Eval-set contamination blocklist (Adversarial-Agent plan §7.4).

When (not if) we benchmark our license-clean corpus against YouCook2,
EPIC-KITCHENS, HD-EPIC, etc., we must guarantee no eval-set videos or
near-duplicates leak into our pretraining shards. This module gives us
a deterministic, offline-evaluable gate.

Design:
  * A `BlocklistEntry` is `(phash64_hex, source, note)`.
  * `Blocklist` stores entries and answers `contains(phash, max_distance)`
    in O(N). For our v0 scale (~10k eval keyframes) this is fine; a
    BK-tree drop-in goes behind the same interface in v1.
  * `Blocklist.load_jsonl(path)` / `.dump_jsonl(path)` round-trip a
    JSON Lines file so a blocklist can be checked into git and reviewed.

The default Hamming threshold is 8 (out of 64) — the same threshold the
day-one plan committed to. A higher threshold is fine but produces more
false-positive exclusions; a lower threshold misses re-encoded
near-duplicates.

Inputs / outputs:
  * `phash_hex` is always a 16-char lowercase hex string (db_structured §2.2).
  * `Blocklist.contains(phash) -> bool`.
  * `Blocklist.distance_to_nearest(phash) -> int in [0, 64]`.

Side effects: file I/O only when `load_jsonl` / `dump_jsonl` are called.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from components.phash import hamming


@dataclass(frozen=True)
class BlocklistEntry:
    phash64: str
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if len(self.phash64) != 16:
            raise ValueError("phash64 must be a 16-char hex string")
        try:
            int(self.phash64, 16)
        except ValueError as exc:
            raise ValueError(f"phash64 must be hex: {self.phash64}") from exc


@dataclass
class Blocklist:
    entries: list[BlocklistEntry] = field(default_factory=list)
    max_distance: int = 8

    def add(self, phash: str, source: str, note: str = "") -> None:
        self.entries.append(BlocklistEntry(phash, source, note))

    def add_many(self, entries: Iterable[BlocklistEntry]) -> None:
        self.entries.extend(entries)

    def distance_to_nearest(self, phash: str) -> int:
        if not self.entries:
            return 64
        return min(hamming(phash, e.phash64) for e in self.entries)

    def contains(self, phash: str, max_distance: int | None = None) -> bool:
        thresh = self.max_distance if max_distance is None else max_distance
        return self.distance_to_nearest(phash) <= thresh

    def reject(
        self, candidates: Iterable[tuple[str, str]], max_distance: int | None = None
    ) -> list[tuple[str, str, int]]:
        """Return ``(id, phash, nearest_distance)`` for candidates that match.

        ``candidates`` is an iterable of ``(id, phash64_hex)`` pairs. The output is
        the subset that fell *inside* the blocklist radius — i.e. the IDs we
        must NOT include in pretraining shards.
        """
        out: list[tuple[str, str, int]] = []
        thresh = self.max_distance if max_distance is None else max_distance
        for cid, ph in candidates:
            d = self.distance_to_nearest(ph)
            if d <= thresh:
                out.append((cid, ph, d))
        return out

    @classmethod
    def load_jsonl(cls, path: str | Path, max_distance: int = 8) -> Blocklist:
        bl = cls(max_distance=max_distance)
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            bl.add(row["phash64"], row.get("source", "unknown"), row.get("note", ""))
        return bl

    def dump_jsonl(self, path: str | Path) -> None:
        lines = [
            json.dumps(
                {"phash64": e.phash64, "source": e.source, "note": e.note},
                sort_keys=True,
            )
            for e in self.entries
        ]
        Path(path).write_text("\n".join(lines) + ("\n" if lines else ""))
