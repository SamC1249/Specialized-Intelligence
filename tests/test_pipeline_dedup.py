from datetime import UTC, datetime

from specint.pipeline import dedupe
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str, title: str = "x", url: str = "https://example.test/a", **overrides
) -> VideoRecord:
    base = dict(
        id=id_,
        source="t",
        source_native_id=id_,
        url=url,
        title=title,
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_dedupe_no_collisions_returns_input_unchanged():
    a = _rec("a", url="https://example.test/1", title="Garlic Butter Pasta")
    b = _rec("b", url="https://example.test/2", title="Chocolate Cake")
    kept, stats = dedupe([a, b])
    assert [r.id for r in kept] == ["a", "b"]
    assert stats.removed == 0


def test_dedupe_url_collision_keeps_higher_quality():
    a = _rec("a", url="https://example.test/1").with_quality(0.4)
    b = _rec("b", url="https://example.test/1").with_quality(0.9)
    kept, stats = dedupe([a, b])
    assert [r.id for r in kept] == ["b"]  # winner is b (higher quality)
    assert kept[0].quality_score == 0.9
    assert stats.n_removed_by_url == 1


def test_dedupe_media_url_collision():
    a = _rec(
        "a",
        url="https://example.test/1",
        media_url="https://cdn.example.test/x.mp4",
        license=License.CC_BY,
    )
    b = _rec(
        "b",
        url="https://example.test/2",
        media_url="https://cdn.example.test/x.mp4",
        license=License.CC_BY,
    )
    kept, stats = dedupe([a, b])
    assert stats.n_removed_by_media_url == 1
    assert len(kept) == 1


def test_dedupe_title_shingle_collision_with_same_author():
    a = _rec(
        "a",
        url="https://example.test/1",
        title="Easy Garlic Butter Pasta",
        author="Sam Cook",
    )
    b = _rec(
        "b",
        url="https://example.test/2",
        title="Easy garlic-butter pasta!",
        author="Sam Cook",
    )
    kept, stats = dedupe([a, b])
    assert len(kept) == 1
    assert stats.n_removed_by_title == 1


def test_dedupe_title_shingle_ignored_when_authors_differ():
    a = _rec(
        "a",
        url="https://example.test/1",
        title="Easy Garlic Butter Pasta",
        author="Sam Cook",
    )
    b = _rec(
        "b",
        url="https://example.test/2",
        title="Easy garlic-butter pasta!",
        author="Other Chef",
    )
    kept, stats = dedupe([a, b])
    assert len(kept) == 2
    assert stats.n_removed_by_title == 0


def test_dedupe_license_tiebreak_prefers_cc0():
    a = _rec("a", url="https://example.test/1", license=License.CC_BY_SA).with_quality(0.5)
    b = _rec("b", url="https://example.test/1", license=License.CC0).with_quality(0.5)
    kept, _ = dedupe([a, b])
    assert kept[0].license is License.CC0


def test_dedupe_stats_totals_add_up():
    a = _rec("a", url="https://example.test/1", title="Alpha")
    b = _rec("b", url="https://example.test/1", title="Alpha")
    c = _rec("c", url="https://example.test/2", title="Beta")
    kept, stats = dedupe([a, b, c])
    assert stats.n_input == 3
    assert stats.n_output == len(kept) == 2
    assert stats.removed == 1
