from __future__ import annotations

from datetime import UTC, datetime

from specint.pipeline import dedup_records
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="s:1",
        source="s",
        source_native_id="1",
        url="https://example.test/1",
        title="A demo",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_dedup_is_idempotent_on_unique_records():
    records = [
        _rec(id="a:1", url="https://a.test/1", title="one"),
        _rec(id="b:2", url="https://b.test/2", title="two"),
    ]
    r = dedup_records(records)
    assert r.counters["n_input"] == 2
    assert r.counters["n_output"] == 2
    assert r.duplicates == {}


def test_dedup_merges_same_url_across_sources_and_keeps_higher_license():
    records = [
        _rec(
            id="cc:1",
            source="common_crawl",
            url="https://example.test/video-1",
            title="Video 1",
            license=License.UNKNOWN,
        ),
        _rec(
            id="wm:2",
            source="wikimedia",
            url="https://example.test/video-1",
            title="Video 1",
            license=License.CC_BY,
        ),
    ]
    r = dedup_records(records)
    assert r.counters["n_output"] == 1
    survivor = r.records[0]
    assert survivor.license is License.CC_BY
    assert survivor.id == "wm:2"


def test_dedup_merges_same_media_url_even_with_different_page_urls():
    records = [
        _rec(
            id="a:1",
            url="https://a.test/1",
            media_url="https://cdn.test/x.mp4",
            license=License.CC0,
        ),
        _rec(
            id="b:2",
            url="https://b.test/2",
            media_url="https://cdn.test/x.mp4",
            license=License.CC_BY,
        ),
    ]
    r = dedup_records(records)
    assert r.counters["n_output"] == 1
    assert r.counters["merged_by_media_url"] == 1
    assert r.records[0].license is License.CC0


def test_dedup_title_shingle_requires_duration_bucket_match():
    records = [
        _rec(
            id="a:1",
            url="https://a.test/1",
            title="Easy Garlic Butter Pasta",
            duration_s=270.0,
        ),
        _rec(
            id="b:2",
            url="https://b.test/2",
            title="Easy Garlic Butter Pasta",
            duration_s=272.0,
        ),
        _rec(
            id="c:3",
            url="https://c.test/3",
            title="Easy Garlic Butter Pasta",
            duration_s=3600.0,
        ),
    ]
    r = dedup_records(records)
    assert r.counters["n_output"] == 2
    survivor_ids = {rec.id for rec in r.records}
    assert "c:3" in survivor_ids


def test_dedup_does_not_merge_short_generic_titles_alone():
    records = [
        _rec(id="a:1", url="https://a.test/1", title="Pasta", duration_s=90.0),
        _rec(id="b:2", url="https://b.test/2", title="Pizza", duration_s=90.0),
    ]
    r = dedup_records(records)
    assert r.counters["n_output"] == 2


def test_dedup_output_is_sorted_by_id_for_reproducibility():
    records = [
        _rec(id="z:1", url="https://z.test/1"),
        _rec(id="a:1", url="https://a.test/1"),
        _rec(id="m:1", url="https://m.test/1"),
    ]
    r = dedup_records(records)
    assert [rec.id for rec in r.records] == ["a:1", "m:1", "z:1"]


def test_dedup_result_serialises_cleanly():
    r = dedup_records([_rec()])
    payload = r.model_dump(mode="json")
    assert payload["counters"]["n_output"] == 1
    assert isinstance(payload["duplicates"], dict)
