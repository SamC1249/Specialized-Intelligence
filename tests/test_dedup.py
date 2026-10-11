from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import dedupe, dedupe_stats, normalise_title
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    id: str,
    title: str,
    duration: float | None,
    license: License,
    source: str = "wikimedia",
    author: str | None = "Chef Example",
    description: str = "",
    height: int | None = 720,
    keywords: list[str] | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=id,
        source=source,
        source_native_id=id.split(":", 1)[-1],
        url=f"https://example.test/{id}",
        media_url=None,
        title=title,
        description=description,
        language="en",
        duration_s=duration,
        width=1280,
        height=height,
        fps=None,
        license=license,
        license_url=None,
        author=author,
        published_at=datetime(2025, 1, 1, tzinfo=UTC),
        keywords=keywords or [],
        recipe_steps=[],
        provenance=Provenance(extractor="tests", fetched_at=datetime.now(UTC), query="q"),
    )


def test_normalise_title_collapses_articles_and_punctuation():
    assert normalise_title("The Best, Easiest Pasta!") == "best easiest pasta"
    assert normalise_title("  Garlic — Butter   Pasta  ") == "garlic butter pasta"
    assert normalise_title("L'omelette parfaite") == "l omelette parfaite"


def test_dedupe_merges_near_duplicate_titles_and_durations():
    group = [
        _rec(
            id="wikimedia:1",
            title="Garlic Butter Pasta",
            duration=301.0,
            license=License.CC_BY_SA,
            source="wikimedia",
            keywords=["pasta", "italian"],
            description="A short description.",
        ),
        _rec(
            id="archive_org:2",
            title="Garlic butter pasta!",
            duration=299.0,
            license=License.CC_BY,
            source="archive_org",
            keywords=["pasta", "mediterranean"],
            description="This one has a much longer description than the Wikimedia mirror does.",
            height=1080,
        ),
    ]
    merged = dedupe(group)
    assert len(merged) == 1
    rep = merged[0]
    # CC-BY outranks CC-BY-SA in LICENSE_RANK, so the Archive copy wins.
    assert rep.id == "archive_org:2"
    assert set(rep.keywords) == {"pasta", "italian", "mediterranean"}


def test_dedupe_prefers_strongest_license_tier():
    group = [
        _rec(id="a:1", title="Risotto", duration=600, license=License.CC_BY_SA),
        _rec(id="b:2", title="Risotto", duration=600, license=License.CC0),
        _rec(id="c:3", title="Risotto", duration=600, license=License.UNKNOWN),
    ]
    merged = dedupe(group)
    assert len(merged) == 1
    assert merged[0].license is License.CC0


def test_dedupe_leaves_distinct_records_alone():
    group = [
        _rec(id="a:1", title="Risotto Milanese", duration=603, license=License.CC_BY),
        _rec(
            id="a:2", title="Risotto Milanese", duration=597, license=License.CC_BY
        ),  # same 10s bucket
        _rec(id="b:3", title="Risotto Nero", duration=800, license=License.CC_BY),
    ]
    merged = dedupe(group)
    assert len(merged) == 2
    assert {r.title for r in merged} == {"Risotto Milanese", "Risotto Nero"}


def test_dedupe_unknown_duration_does_not_collapse():
    group = [
        _rec(id="a:1", title="Mystery Dish", duration=None, license=License.CC_BY),
        _rec(id="a:2", title="Mystery Dish", duration=120, license=License.CC_BY),
    ]
    merged = dedupe(group)
    assert len(merged) == 2


def test_dedupe_stats_shape():
    before = [_rec(id="x:1", title="A", duration=100, license=License.CC_BY)]
    after = dedupe(before)
    stats = dedupe_stats(before, after)
    assert stats == {"before": 1, "after": 1, "removed": 0}
