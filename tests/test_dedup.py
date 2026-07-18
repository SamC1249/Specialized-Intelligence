"""Tests for cross-source dedup.

See `docs/plan-2026-07-18.md` §A1 for the hypothesis being tested.
"""

from __future__ import annotations

from specint.dedup import (
    canonical_url,
    dedup,
    dedup_report,
    duration_bucket,
    group_duplicates,
    normalized_title,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    id: str,
    source: str,
    url: str,
    title: str,
    duration_s: float | None = 120.0,
    license: License = License.CC_BY,
) -> VideoRecord:
    return VideoRecord(
        id=id,
        source=source,
        source_native_id=id.split(":", 1)[-1],
        url=url,
        title=title,
        duration_s=duration_s,
        license=license,
        provenance=Provenance(extractor="test"),
    )


class TestCanonicalization:
    def test_canonical_url_strips_www_query_fragment(self):
        a = canonical_url("https://WWW.Example.com/path/?utm=abc#foo")
        b = canonical_url("https://example.com/path")
        assert a == b == "https://example.com/path"

    def test_canonical_url_trailing_slash(self):
        assert canonical_url("https://x.io/a/") == canonical_url("https://x.io/a")

    def test_normalized_title_drops_noise_tokens(self):
        assert normalized_title("Cooking Pasta 1080p Official HD") == normalized_title(
            "cooking pasta"
        )

    def test_duration_bucket_none_for_missing(self):
        assert duration_bucket(None) is None
        assert duration_bucket(0) is None
        assert duration_bucket(-1.5) is None

    def test_duration_bucket_rounds(self):
        assert duration_bucket(120.0) == duration_bucket(121.0) == duration_bucket(119.0)


class TestGrouping:
    def test_exact_url_match_across_sources(self):
        a = _rec(id="wikimedia:1", source="wikimedia", url="https://example.org/v/a", title="A")
        b = _rec(
            id="archive_org:x",
            source="archive_org",
            url="https://example.org/v/a/",
            title="different title",
        )
        groups = group_duplicates([a, b])
        assert len(groups) == 1
        assert {r.id for r in groups[0]} == {"wikimedia:1", "archive_org:x"}

    def test_title_and_duration_match(self):
        a = _rec(
            id="wikimedia:2",
            source="wikimedia",
            url="https://commons.wikimedia.org/wiki/File:Pasta.webm",
            title="Cooking Pasta 1080p",
            duration_s=180.0,
        )
        b = _rec(
            id="archive_org:pasta-video",
            source="archive_org",
            url="https://archive.org/details/pasta-video",
            title="cooking pasta HD",
            duration_s=182.0,
        )
        groups = group_duplicates([a, b])
        assert len(groups) == 1

    def test_no_false_merge_on_different_duration(self):
        a = _rec(
            id="wikimedia:3",
            source="wikimedia",
            url="https://a.test/1",
            title="Cooking Pasta",
            duration_s=60.0,
        )
        b = _rec(
            id="archive_org:3",
            source="archive_org",
            url="https://b.test/1",
            title="Cooking Pasta",
            duration_s=600.0,
        )
        groups = group_duplicates([a, b])
        assert len(groups) == 2


class TestSurvivorPolicy:
    def test_strongest_license_wins(self):
        weak = _rec(
            id="peertube:x",
            source="peertube",
            url="https://p.test/1",
            title="Same",
            duration_s=100.0,
            license=License.UNKNOWN,
        )
        strong = _rec(
            id="wikimedia:y",
            source="wikimedia",
            url="https://w.test/1",
            title="Same",
            duration_s=100.0,
            license=License.CC0,
        )
        survivors = dedup([weak, strong])
        assert len(survivors) == 1
        assert survivors[0].license is License.CC0
        assert survivors[0].id == "wikimedia:y"

    def test_never_upgrades_license_from_restricted(self):
        r1 = _rec(
            id="a:1",
            source="a",
            url="https://x.test/x",
            title="Same",
            duration_s=50.0,
            license=License.RESTRICTED,
        )
        r2 = _rec(
            id="a:2",
            source="b",
            url="https://x.test/x",
            title="Same",
            duration_s=50.0,
            license=License.UNKNOWN,
        )
        survivors = dedup([r1, r2])
        # Higher priority is UNKNOWN over RESTRICTED — the survivor must not silently
        # become "clean". Both are non-redistributable; assert that.
        assert len(survivors) == 1
        assert not survivors[0].license.is_redistributable


class TestReport:
    def test_dedup_report_counts_duplicates(self):
        a = _rec(id="w:1", source="wikimedia", url="https://z.test/a", title="X", duration_s=30.0)
        b = _rec(
            id="w:2", source="wikimedia", url="https://z.test/a", title="X-copy", duration_s=30.0
        )
        c = _rec(id="w:3", source="wikimedia", url="https://z.test/b", title="Y", duration_s=90.0)
        report = dedup_report([a, b, c])
        assert report == {"n_input": 3, "n_unique_groups": 2, "n_duplicates": 1}

    def test_empty_input(self):
        assert dedup([]) == []
        assert dedup_report([]) == {"n_input": 0, "n_unique_groups": 0, "n_duplicates": 0}
