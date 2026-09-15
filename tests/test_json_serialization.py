"""Round-trip guardrail: fixtures → records → scores → JSON → reload.

Catches silent drift in Pydantic serialization (e.g. an accidentally-added
non-JSON-safe field, a timezone-naive datetime, or a `AnyHttpUrl` that
serializes with a trailing slash on one Python version but not another).

The invariant is byte-equality of `json.dumps(..., sort_keys=True)` on
two independent serialization passes of the same records.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.records import BenchmarkResult, SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _fixture_records(fixtures_dir: Path) -> dict[str, list[VideoRecord]]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    return {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }


def test_video_record_round_trip_is_byte_stable(fixtures_dir: Path):
    all_records: list[VideoRecord] = []
    for records in _fixture_records(fixtures_dir).values():
        all_records.extend(records)

    assert all_records, "expected non-empty fixture set"

    first = json.dumps(
        [r.model_dump(mode="json") for r in all_records],
        sort_keys=True,
    )
    reloaded = [VideoRecord(**obj) for obj in json.loads(first)]
    second = json.dumps(
        [r.model_dump(mode="json") for r in reloaded],
        sort_keys=True,
    )
    assert first == second


def test_benchmark_result_round_trip_is_byte_stable(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, _fixture_records(fixtures_dir), notes="roundtrip")

    first = json.dumps([r.model_dump(mode="json") for r in rows], sort_keys=True)
    reloaded = [BenchmarkResult(**obj) for obj in json.loads(first)]
    second = json.dumps([r.model_dump(mode="json") for r in reloaded], sort_keys=True)
    assert first == second


@pytest.mark.parametrize("field", ["provenance", "url", "license"])
def test_video_record_required_fields_present(field: str, fixtures_dir: Path):
    """Ensure no adapter accidentally omits a required field."""
    for records in _fixture_records(fixtures_dir).values():
        for r in records:
            assert getattr(r, field) is not None, f"{r.id}: missing {field}"


def test_full_report_matches_ci_shape(fixtures_dir: Path, tmp_path: Path):
    """The report shape emitted here must match `python -m specint compare`."""
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, _fixture_records(fixtures_dir), notes="ci-shape-check")

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "report.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    reloaded = json.loads(out.read_text())

    assert set(reloaded) == {"query", "rows"}
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    row_sources = {r["source"] for r in reloaded["rows"]}
    assert "__total__" in row_sources
    assert row_sources - {"__total__"} == {
        "archive_org",
        "common_crawl",
        "peertube",
        "wikimedia",
    }
