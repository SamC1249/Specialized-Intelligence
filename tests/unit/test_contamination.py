from __future__ import annotations

import json

import pytest

from specint.contamination import Blocklist, BlocklistEntry


def test_entry_validates_hex_and_length():
    with pytest.raises(ValueError):
        BlocklistEntry(phash64="zz", source="eval")
    with pytest.raises(ValueError):
        BlocklistEntry(phash64="abc", source="eval")
    BlocklistEntry(phash64="0123456789abcdef", source="eval")


def test_contains_exact_and_within_radius():
    bl = Blocklist(max_distance=4)
    bl.add("0000000000000000", source="youcook2", note="seed-keyframe")
    # exact match
    assert bl.contains("0000000000000000")
    # 1-bit difference
    assert bl.contains("0000000000000001")
    # many bits flipped -> outside default radius
    assert not bl.contains("ffffffffffffffff")


def test_default_max_distance_is_eight():
    bl = Blocklist()
    bl.add("0000000000000000", source="eval")
    # 8 bits flipped (0xff in lowest byte) -> still in
    assert bl.contains("00000000000000ff")
    # 9 bits flipped (0x1ff -> 9 bits set) -> just out
    assert not bl.contains("00000000000001ff")


def test_distance_to_nearest_empty_blocklist():
    bl = Blocklist()
    assert bl.distance_to_nearest("0000000000000000") == 64


def test_reject_returns_offending_candidates():
    bl = Blocklist(max_distance=4)
    bl.add("0000000000000000", source="eval")
    rejected = bl.reject(
        [
            ("a", "0000000000000000"),
            ("b", "0000000000000001"),
            ("c", "ffffffffffffffff"),
        ]
    )
    ids = {r[0] for r in rejected}
    assert ids == {"a", "b"}


def test_jsonl_roundtrip(tmp_path):
    bl = Blocklist(max_distance=8)
    bl.add("0123456789abcdef", source="epic_kitchens", note="train clip 12.frame_30")
    bl.add("fedcba9876543210", source="youcook2", note="val clip 3.frame_5")
    path = tmp_path / "bl.jsonl"
    bl.dump_jsonl(path)
    loaded = Blocklist.load_jsonl(path, max_distance=8)
    assert {(e.phash64, e.source) for e in loaded.entries} == {
        (e.phash64, e.source) for e in bl.entries
    }


def test_jsonl_comments_skipped(tmp_path):
    path = tmp_path / "bl.jsonl"
    body = "\n".join(
        [
            "# YouCook2 v0 blocklist",
            json.dumps({"phash64": "0123456789abcdef", "source": "youcook2"}),
            "",
            json.dumps({"phash64": "fedcba9876543210", "source": "youcook2"}),
        ]
    )
    path.write_text(body)
    loaded = Blocklist.load_jsonl(path)
    assert len(loaded.entries) == 2
