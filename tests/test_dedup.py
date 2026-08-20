"""Tests for `specint.dedup.minhash`."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedup import dedup_records, minhash_signature
from specint.records import License, Provenance, VideoRecord


def _rec(rid: str, title: str, **kw) -> VideoRecord:
    base = dict(
        id=rid,
        source=kw.pop("source", "src"),
        source_native_id=rid.split(":")[-1],
        url=kw.pop("url", f"https://example.test/{rid.replace(':', '/')}"),
        title=title,
        description=kw.pop("description", ""),
        license=kw.pop("license", License.UNKNOWN),
        width=kw.pop("width", None),
        height=kw.pop("height", None),
        published_at=kw.pop("published_at", None),
        provenance=Provenance(extractor="t"),
    )
    base.update(kw)
    return VideoRecord(**base)


def test_minhash_signature_stable_and_similar_for_near_duplicates():
    a = minhash_signature("How to make garlic butter pasta at home step by step")
    b = minhash_signature("How to make Garlic Butter Pasta at home, step by step!")
    same = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    assert same / len(a) >= 0.7
    assert a == minhash_signature("How to make garlic butter pasta at home step by step")


def test_minhash_signature_diverges_for_unrelated_titles():
    a = minhash_signature("Knife skills chopping onions demonstration")
    b = minhash_signature("Deep sea diving in the Great Barrier Reef")
    same = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    assert same / len(a) < 0.3


def test_dedup_collapses_near_duplicates_across_sources():
    records = [
        _rec(
            "wikimedia:1",
            "Knife skills chopping onions demonstration",
            source="wikimedia",
            license=License.CC_BY_SA,
            width=1920,
            height=1080,
            published_at=datetime(2019, 1, 1, tzinfo=UTC),
        ),
        _rec(
            "archive_org:knife-skills-2019",
            "knife skills: chopping onions demonstration",
            source="archive_org",
            license=License.UNKNOWN,
            width=640,
            height=480,
            published_at=datetime(2022, 5, 1, tzinfo=UTC),
        ),
        _rec(
            "peertube:tomato-soup",
            "Easy tomato tortellini soup recipe",
            source="peertube",
            license=License.CC_BY,
        ),
    ]
    result = dedup_records(records)
    assert result.n_duplicates_removed == 1
    # Canonical for the collapse should be the CC-BY-SA 1080p item.
    [group] = result.collapsed_groups
    assert group[0].id == "wikimedia:1"
    # Order-preserving on kept records.
    kept_ids = [r.id for r in result.kept]
    assert kept_ids == ["wikimedia:1", "peertube:tomato-soup"]


def test_dedup_no_collision_returns_all():
    records = [
        _rec("a:1", "Making sourdough bread"),
        _rec("b:2", "Filleting a whole fish"),
        _rec("c:3", "Building a wood-fired pizza oven"),
    ]
    result = dedup_records(records)
    assert result.n_duplicates_removed == 0
    assert len(result.kept) == 3
    assert result.collapsed_groups == []


def test_dedup_prefers_higher_license_tier_over_earlier_publish():
    records = [
        _rec(
            "restricted:old",
            "How to bake a chocolate cake at home step by step",
            license=License.RESTRICTED,
            published_at=datetime(2000, 1, 1, tzinfo=UTC),
            width=1920,
            height=1080,
        ),
        _rec(
            "cc0:new",
            "How to bake a chocolate cake at home, step by step",
            license=License.CC0,
            published_at=datetime(2024, 1, 1, tzinfo=UTC),
            width=640,
            height=480,
        ),
    ]
    result = dedup_records(records)
    assert result.n_duplicates_removed == 1
    [group] = result.collapsed_groups
    assert group[0].id == "cc0:new"


def test_dedup_empty_input():
    result = dedup_records([])
    assert result.kept == []
    assert result.collapsed_groups == []
