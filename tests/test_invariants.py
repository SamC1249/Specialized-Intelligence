"""Cross-source invariants: license/media-URL safety, id namespacing.

Runs the invariant check against every adapter's fixture parse output,
so a new adapter physically cannot merge without either passing the
invariants or explicitly amending them here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.quality.invariants import (
    InvariantViolation,
    assert_records,
    check_records,
    summarize,
)
from specint.records import License, Provenance, SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _prov() -> Provenance:
    return Provenance(extractor="tests", fetched_at=datetime.now(UTC), query="")


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="wikimedia:1",
        source="wikimedia",
        source_native_id="1",
        url="https://example.test/1",
        title="t",
        license=License.CC_BY,
        provenance=_prov(),
    )
    base.update(overrides)
    return VideoRecord(**base)


class TestInvariantPositive:
    def test_clean_record_has_no_violations(self):
        assert check_records([_rec()]) == []

    def test_batch_summary_reports_zero(self):
        assert summarize([]) == {"n_violations": 0, "by_code": {}}


class TestI4RestrictedMediaUrl:
    def test_restricted_with_media_url_violates(self):
        r = _rec(license=License.RESTRICTED, media_url="https://example.test/media.mp4")
        violations = check_records([r])
        assert any(v.code == "I4" for v in violations)

    def test_unknown_with_media_url_violates(self):
        r = _rec(license=License.UNKNOWN, media_url="https://example.test/media.mp4")
        violations = check_records([r])
        assert any(v.code == "I4" for v in violations)

    def test_cc_by_with_media_url_ok(self):
        r = _rec(license=License.CC_BY, media_url="https://example.test/media.mp4")
        assert not any(v.code == "I4" for v in check_records([r]))


class TestI5UniqueIds:
    def test_duplicate_id_flagged(self):
        a = _rec(id="wikimedia:1")
        b = _rec(id="wikimedia:1", url="https://example.test/2")
        assert any(v.code == "I5" for v in check_records([a, b]))


class TestI6SourceIdPrefixMatch:
    def test_mismatched_prefix_flagged(self):
        r = _rec(id="archive_org:1", source="wikimedia")
        assert any(v.code == "I6" for v in check_records([r]))


class TestAssertRecordsRaises:
    def test_assert_raises_on_violation(self):
        r = _rec(license=License.RESTRICTED, media_url="https://example.test/media.mp4")
        with pytest.raises(AssertionError, match=r"invariant violation"):
            assert_records([r])


class TestAdaptersProduceInvariantCleanRecords:
    """Every registered adapter's fixture output must pass all invariants."""

    def _query(self) -> SourceQuery:
        return SourceQuery(terms=["cooking"], max_results=25)

    def test_wikimedia_fixture(self, fixtures_dir: Path):
        raw = json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())
        records = WikimediaCommonsSource().parse(raw, self._query())
        assert_records(records)

    def test_archive_org_fixture(self, fixtures_dir: Path):
        raw = json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text())
        records = ArchiveOrgSource().parse(raw, self._query())
        assert_records(records)

    def test_peertube_fixture(self, fixtures_dir: Path):
        raw = json.loads((fixtures_dir / "peertube/search_cooking.json").read_text())
        records = PeerTubeSource().parse(raw, self._query())
        assert_records(records)

    def test_common_crawl_fixture(self, fixtures_dir: Path):
        html = (fixtures_dir / "common_crawl/recipe_page.html").read_text()
        records = CommonCrawlRecipeSource().parse(
            {"html": html, "url": "https://example.test/recipes/garlic-butter-pasta"},
            self._query(),
        )
        assert_records(records)

    def test_registry_completeness(self):
        assert set(REGISTRY.keys()) == {
            "wikimedia",
            "archive_org",
            "peertube",
            "common_crawl",
        }


class TestSummarize:
    def test_by_code_counts(self):
        v = [
            InvariantViolation("I4", "a", "x"),
            InvariantViolation("I4", "b", "y"),
            InvariantViolation("I5", "a", "z"),
        ]
        assert summarize(v) == {"n_violations": 3, "by_code": {"I4": 2, "I5": 1}}
