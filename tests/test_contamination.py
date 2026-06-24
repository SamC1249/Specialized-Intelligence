from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.contamination import (
    Blocklist,
    BlocklistEntry,
    filter_contaminated,
    normalize_title,
)
from specint.records import Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base: dict = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="A clip",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_normalize_title_lowercases_strips_punct_and_stops():
    assert normalize_title("How to Cook Pasta!") == "cook pasta"
    assert normalize_title("KNIFE skills: slicing onions") == "knife skills slicing onions"
    assert normalize_title("Sauté the onion") == "saute onion"
    assert normalize_title("") == ""
    assert normalize_title("   the the the   ") == ""


def test_blocklist_round_trip_via_load(fixtures_dir: Path):
    bl = Blocklist.load(fixtures_dir / "blocklists/youcook2_sample.jsonl")
    assert "cook pasta" in bl.titles
    assert "knife skills slicing onions" in bl.titles
    assert "https://archive.org/details/cooking_demo_1958" in bl.urls
    assert "peertube:demo-abc-123" in bl.native_ids
    assert "0123456789abcdef" in bl.phash16


def test_blocklist_matches_title_native_id_and_url():
    bl = Blocklist.from_entries(
        [
            BlocklistEntry(kind="title_norm", value="How to Cook Pasta"),
            BlocklistEntry(kind="native_id", value="peertube:demo-abc-123"),
            BlocklistEntry(kind="url", value="https://archive.org/details/cooking_demo_1958/"),
        ]
    )

    title_hit = _rec(title="how to cook PASTA")
    id_hit = _rec(source_native_id="peertube:demo-abc-123")
    url_hit = _rec(url="https://archive.org/details/cooking_demo_1958")
    clean = _rec(title="Something unrelated", source_native_id="x", url="https://example.test/y")

    assert bl.contains(title_hit)
    assert bl.contains(id_hit)
    assert bl.contains(url_hit)
    assert not bl.contains(clean)


def test_filter_contaminated_returns_kept_and_dropped(fixtures_dir: Path):
    bl = Blocklist.load(fixtures_dir / "blocklists/youcook2_sample.jsonl")
    records = [
        _rec(id="t:keep", title="A new soup recipe"),
        _rec(id="t:drop-1", title="How to Cook Pasta"),
        _rec(id="t:drop-2", source_native_id="peertube:demo-abc-123"),
    ]
    kept, dropped = filter_contaminated(records, bl)
    assert {r.id for r in kept} == {"t:keep"}
    assert {r.id for r in dropped} == {"t:drop-1", "t:drop-2"}


def test_blocklist_rejects_unknown_kind():
    with pytest.raises(ValueError):
        BlocklistEntry(kind="garbage", value="x")


def test_empty_blocklist_is_a_noop():
    bl = Blocklist.from_entries([])
    assert bl.is_empty()
    rec = _rec()
    assert not bl.contains(rec)
    kept, dropped = filter_contaminated([rec], bl)
    assert kept == [rec]
    assert dropped == []
