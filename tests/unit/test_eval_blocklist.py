"""Unit tests for components.eval_blocklist."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from components.eval_blocklist import BlockHit, BlockList, apply, load_blocklist

# A few hand-picked hashes. We craft them so we know the Hamming distances
# without doing math at runtime.
HASH_A = "0000000000000000"
HASH_A_NEAR = "0000000000000001"  # distance 1
HASH_A_FAR = "ffffffffffffffff"  # distance 64
HASH_B = "deadbeefdeadbeef"


def test_load_blocklist_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "blocklist.jsonl"
    rows = [
        {"phash64": HASH_A, "source": "epic_kitchens"},
        {"phash64": HASH_B, "source": "hd_epic"},
        {"phash64": HASH_A, "source": "duplicate"},  # dup; should dedupe
    ]
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    loaded = load_blocklist(src)
    assert loaded == [HASH_A, HASH_B]


def test_load_blocklist_rejects_bad_rows(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.jsonl"
    bad_json.write_text("not json\n")
    with pytest.raises(ValueError):
        load_blocklist(bad_json)

    missing_field = tmp_path / "missing.jsonl"
    missing_field.write_text(json.dumps({"source": "x"}) + "\n")
    with pytest.raises(ValueError):
        load_blocklist(missing_field)

    bad_hash = tmp_path / "bh.jsonl"
    bad_hash.write_text(json.dumps({"phash64": "zz"}) + "\n")
    with pytest.raises(ValueError):
        load_blocklist(bad_hash)


def test_blocklist_threshold_bounds() -> None:
    with pytest.raises(ValueError):
        BlockList([HASH_A], threshold=-1)
    with pytest.raises(ValueError):
        BlockList([HASH_A], threshold=65)
    BlockList([HASH_A], threshold=0)
    BlockList([HASH_A], threshold=64)


def test_blocklist_contains_and_nearest_within_threshold() -> None:
    bl = BlockList([HASH_A, HASH_B], threshold=2)
    assert bl.contains(HASH_A)
    assert bl.contains(HASH_A_NEAR)
    hit = bl.nearest(HASH_A_NEAR)
    assert isinstance(hit, BlockHit)
    assert hit.phash == HASH_A
    assert hit.distance == 1


def test_blocklist_misses_outside_threshold() -> None:
    bl = BlockList([HASH_A], threshold=2)
    assert not bl.contains(HASH_A_FAR)
    assert bl.nearest(HASH_A_FAR) is None


def test_apply_marks_excluded_and_preserves_input() -> None:
    bl = BlockList([HASH_A], threshold=1)
    clips = [
        {"clip_id": "1" * 16, "phash64": HASH_A_NEAR, "excluded": False, "exclusion_reason": None},
        {"clip_id": "2" * 16, "phash64": HASH_B, "excluded": False, "exclusion_reason": None},
    ]
    out = apply(clips, bl)
    assert out[0]["excluded"] is True
    assert "eval_blocklist_hit" in out[0]["exclusion_reason"]
    assert "d=1" in out[0]["exclusion_reason"]
    assert out[1]["excluded"] is False
    # Inputs must not have been mutated.
    assert clips[0]["excluded"] is False
    assert clips[1]["excluded"] is False


def test_apply_raises_on_missing_phash() -> None:
    bl = BlockList([HASH_A], threshold=1)
    with pytest.raises(ValueError):
        apply([{"clip_id": "x" * 16, "phash64": None}], bl)
