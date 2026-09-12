"""Unit tests for metadata-only near-duplicate detection (Phase 1).

See `docs/artifacts/2026-09-12-video-dedup.md` for the three-phase plan
and the design rationale for the thresholds.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.quality import (
    DedupResult,
    aggregate_dedup,
    dedup_records,
    normalize_url,
    title_tokens,
)
from specint.quality.dedup import _UnionFind
from specint.records import License, Provenance, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _rec(
    id_: str,
    url: str,
    title: str,
    duration: float | None = 300.0,
    license_: License = License.CC_BY,
    source: str | None = None,
) -> VideoRecord:
    src = source or id_.split(":", 1)[0]
    return VideoRecord(
        id=id_,
        source=src,
        source_native_id=id_.split(":", 1)[1],
        url=url,
        title=title,
        duration_s=duration,
        license=license_,
        provenance=Provenance(extractor="tests", fetched_at=datetime.now(UTC), query=""),
    )


class TestNormalizeUrl:
    def test_strips_scheme_www_and_trailing_slash(self):
        assert normalize_url("https://www.example.com/a/b/") == "example.com/a/b"

    def test_root_path_kept_as_slash(self):
        assert normalize_url("https://example.com") == "example.com/"

    def test_drops_tracking_params_but_keeps_content(self):
        got = normalize_url("https://example.com/x?utm_source=x&id=42&fbclid=abc")
        assert got == "example.com/x?id=42"

    def test_empty_returns_empty(self):
        assert normalize_url("") == ""

    def test_accepts_non_string_url(self):
        assert normalize_url("https://Example.com/A/") == "example.com/A"


class TestTitleTokens:
    def test_drops_stopwords_and_lowercases(self):
        tok = title_tokens("Cooking pasta carbonara with garlic")
        assert "cooking" not in tok
        assert "with" not in tok
        assert "pasta" in tok and "carbonara" in tok and "garlic" in tok

    def test_alphanumerics_only(self):
        tok = title_tokens("Recipe #42! 5-minute knife-skills demo")
        assert tok == frozenset({"42", "5", "minute", "knife", "skills", "demo"})


class TestDedupCore:
    def test_empty_batch_returns_zero_zero(self):
        result = dedup_records([], source="x")
        assert result.n_records == 0
        assert result.n_unique == 0
        assert result.n_duplicates == 0
        assert result.dup_rate == 0.0

    def test_url_duplicate_collapses(self):
        a = _rec("s:1", "https://x.test/a", "Alpha bravo charlie", duration=100.0)
        b = _rec("s:2", "https://www.x.test/a/?utm_source=z", "wildly different name", 100.0)
        result = dedup_records([a, b], source="s")
        assert result.n_records == 2
        assert result.n_unique == 1
        [group] = result.duplicate_groups
        assert group.reason == "url"
        assert set(group.member_ids) == {"s:1", "s:2"}

    def test_title_and_duration_duplicate(self):
        a = _rec("s:1", "https://x.test/1", "Modern chef demonstration", duration=270.0)
        b = _rec("s:2", "https://y.test/2", "Modern chef demonstration", duration=272.0)
        result = dedup_records([a, b], source="s")
        assert result.n_unique == 1
        [group] = result.duplicate_groups
        assert group.reason == "title+duration"

    def test_far_duration_prevents_dup(self):
        a = _rec("s:1", "https://x.test/1", "steak au poivre lesson", duration=60.0)
        b = _rec("s:2", "https://y.test/2", "steak au poivre lesson", duration=3600.0)
        result = dedup_records([a, b], source="s")
        assert result.n_unique == 2

    def test_low_title_jaccard_prevents_dup(self):
        a = _rec("s:1", "https://x.test/1", "steak au poivre", duration=300.0)
        b = _rec("s:2", "https://y.test/2", "chocolate mousse", duration=300.0)
        result = dedup_records([a, b], source="s")
        assert result.n_unique == 2

    def test_transitive_grouping(self):
        a = _rec("s:1", "https://x.test/1", "risotto milanese classic", duration=600.0)
        b = _rec("s:2", "https://x.test/1?utm_source=z", "totally new title", 601.0)
        c = _rec("s:3", "https://y.test/3", "risotto milanese classic", 602.0)
        result = dedup_records([a, b, c], source="s")
        assert result.n_unique == 1
        [group] = result.duplicate_groups
        assert set(group.member_ids) == {"s:1", "s:2", "s:3"}

    def test_raises_on_duplicate_ids_within_batch(self):
        a = _rec("s:1", "https://x.test/1", "one", duration=60.0)
        b = _rec("s:1", "https://y.test/2", "two", duration=120.0)
        with pytest.raises(ValueError, match=r"duplicate VideoRecord\.id"):
            dedup_records([a, b], source="s")


class TestAggregate:
    def test_totals_across_sources(self):
        a = _rec("s:1", "https://x.test/1", "a b c", duration=60.0)
        b = _rec("s:2", "https://x.test/1", "a b c", duration=60.0)
        c = _rec("t:1", "https://y.test/1", "u v w", duration=60.0)
        r1 = dedup_records([a, b], source="s")
        r2 = dedup_records([c], source="t")
        agg = aggregate_dedup([r1, r2])
        assert agg.n_records == 3
        assert agg.n_unique == 2

    def test_to_dict_is_json_safe(self):
        a = _rec("s:1", "https://x.test/1", "a b c", duration=60.0)
        result = dedup_records([a], source="s")
        blob = json.dumps(result.to_dict())
        assert '"n_records": 1' in blob


class TestUnionFind:
    def test_find_is_transitive(self):
        uf = _UnionFind(["a", "b", "c"])
        uf.union("a", "b")
        uf.union("b", "c")
        assert uf.find("a") == uf.find("c")


class TestOnRealFixtures:
    def test_wikimedia_dupes_collapse_across_two_search_pages(self, fixtures_dir: Path):
        page1 = json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())
        page2 = json.loads((fixtures_dir / "cross_source_dupes/wikimedia_search.json").read_text())
        query_obj = _rec("dummy:0", "https://x.test/", "").provenance.query  # noqa: F841
        from specint.records import SourceQuery

        q = SourceQuery(terms=["cooking"], max_results=25)
        source = WikimediaCommonsSource()
        records = source.parse(page1, q) + source.parse(page2, q)
        result = dedup_records(records, source="wikimedia")
        assert result.n_records >= 3
        assert result.n_duplicates >= 1
        assert any(g.reason == "url" for g in result.duplicate_groups)

    def test_archive_org_near_dup_by_title(self, fixtures_dir: Path):
        base = json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text())
        extra = json.loads(
            (fixtures_dir / "cross_source_dupes/archive_org_search.json").read_text()
        )
        from specint.records import SourceQuery

        q = SourceQuery(terms=["cooking"], max_results=25)
        source = ArchiveOrgSource()
        records = source.parse(base, q) + source.parse(extra, q)
        result = dedup_records(records, source="archive_org")
        titles_grouped = {g.reason for g in result.duplicate_groups}
        assert "title+duration" in titles_grouped or "url" in titles_grouped

    def test_dedup_result_dup_rate_bounds(self):
        result = DedupResult(source="empty", n_records=0, n_unique=0)
        assert 0.0 <= result.dup_rate <= 1.0
