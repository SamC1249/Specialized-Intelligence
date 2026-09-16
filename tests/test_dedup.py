"""Cross-source deduplication tests.

Focus: cross-source duplicate resolution is deterministic and prefers
higher-quality / redistributable records.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.dedup import dedup_key, deduplicate
from specint.records import License, Provenance, VideoRecord


def _prov() -> Provenance:
    return Provenance(extractor="test", fetched_at=datetime.now(UTC), query="")


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="s:1",
        source="s",
        source_native_id="1",
        url="https://example.test/1",
        title="A cooking video",
        provenance=_prov(),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_dedup_key_prefers_media_url():
    r = _rec(media_url="https://cdn.test/A.mp4", license=License.CC0)
    assert dedup_key(r) == "media:cdn.test/A.mp4"


def test_dedup_key_url_case_and_trailing_slash_insensitive():
    r1 = _rec(media_url="https://CDN.Test/a.mp4")
    r2 = _rec(media_url="https://cdn.test/a.mp4/")
    assert dedup_key(r1) == dedup_key(r2)


def test_dedup_key_falls_back_to_native_id_when_url_shaped():
    r = _rec(
        id="common_crawl:https://commons.wikimedia.org/wiki/File:X.webm",
        source="common_crawl",
        source_native_id="https://commons.wikimedia.org/wiki/File:X.webm",
    )
    assert dedup_key(r) == "media:commons.wikimedia.org/wiki/File:X.webm"


def test_dedup_key_falls_back_to_title_and_duration_bucket(monkeypatch):
    from specint.quality import dedup as dedup_mod

    monkeypatch.setattr(dedup_mod, "_normalize_url", lambda _: None)
    r = _rec(
        id="x:1",
        title="Chicken Curry Tutorial",
        duration_s=310.0,
    )
    r2 = _rec(
        id="x:2",
        title="Chicken curry TUTORIAL!",
        duration_s=312.0,
    )
    assert dedup_key(r) == dedup_key(r2)


def test_deduplicate_prefers_higher_quality():
    a = _rec(id="s:a", source="wikimedia", media_url="https://cdn.test/a.mp4").with_quality(0.9)
    b = _rec(
        id="s:b",
        source="common_crawl",
        media_url="https://cdn.test/a.mp4",
    ).with_quality(0.3)
    result = deduplicate([a, b])
    assert len(result.kept) == 1
    assert result.kept[0].id == "s:a"
    assert result.n_dropped == 1


def test_deduplicate_keeps_keyless_records(monkeypatch):
    from specint.quality import dedup as dedup_mod

    monkeypatch.setattr(dedup_mod, "_normalize_url", lambda _: None)
    a = _rec(id="s:1", title="", duration_s=None)
    b = _rec(id="s:2", title="", duration_s=None)
    result = deduplicate([a, b])
    assert len(result.kept) == 2
    assert result.n_dropped == 0


def test_deduplicate_deterministic_on_ties():
    a = _rec(id="s:a", source="a_src", media_url="https://cdn.test/x.mp4").with_quality(0.5)
    b = _rec(id="s:b", source="b_src", media_url="https://cdn.test/x.mp4").with_quality(0.5)
    # tie on quality → license tie (both UNKNOWN → non-redistributable) →
    # lexicographically first source wins.
    result = deduplicate([b, a, b])
    assert [r.id for r in result.kept] == ["s:a"]


def test_deduplicate_respects_redistributable_tiebreak():
    a = _rec(id="s:1", source="src", media_url="https://cdn.test/y.mp4", license=License.CC0)
    b = _rec(
        id="s:2",
        source="asrc",
        media_url="https://cdn.test/y.mp4",
        license=License.UNKNOWN,
    )
    a = a.with_quality(0.5)
    b = b.with_quality(0.5)
    result = deduplicate([a, b])
    assert result.kept[0].id == "s:1"


def test_group_records_source_ordering():
    a = _rec(id="s:a", source="alpha", media_url="https://cdn.test/z.mp4").with_quality(0.4)
    b = _rec(id="s:b", source="beta", media_url="https://cdn.test/z.mp4").with_quality(0.9)
    result = deduplicate([a, b])
    key = "media:cdn.test/z.mp4"
    assert result.groups[key][0] == "s:b"
    assert set(result.groups[key]) == {"s:a", "s:b"}
