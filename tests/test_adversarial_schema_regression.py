"""Adversarial schema-regression test.

`db_structured.md` is the *canonical* schema. Downstream tools
(analytics notebooks, dashboards, third-party ingestion) read
`reports/*.json` and expect a stable field set. A silent removal or
rename of a `BenchmarkResult` / `VideoRecord` / `Provenance` field is
a breaking change we must catch in CI before it ships.

This test pins a snapshot of the required field set. Adding fields is
always allowed. Removing or renaming a field will fail this test and
force the author to update the snapshot **and** `db_structured.md` in
the same PR.
"""

from __future__ import annotations

from typing import Any

from specint.records import (
    BenchmarkResult,
    License,
    Provenance,
    SourceQuery,
    VideoRecord,
)

VIDEO_RECORD_REQUIRED_FIELDS: set[str] = {
    "id",
    "source",
    "source_native_id",
    "url",
    "media_url",
    "title",
    "description",
    "language",
    "duration_s",
    "width",
    "height",
    "fps",
    "license",
    "license_url",
    "author",
    "published_at",
    "keywords",
    "recipe_steps",
    "provenance",
    "quality_score",
}

PROVENANCE_REQUIRED_FIELDS: set[str] = {
    "extractor",
    "extractor_git",
    "fetched_at",
    "query",
}

SOURCE_QUERY_REQUIRED_FIELDS: set[str] = {
    "terms",
    "max_results",
    "language",
}

BENCHMARK_RESULT_REQUIRED_FIELDS: set[str] = {
    "source",
    "query_terms",
    "n_records",
    "n_license_clean",
    "total_duration_s",
    "mean_quality",
    "p50_quality",
    "p90_quality",
    "unique_authors",
    "notes",
}

REQUIRED_LICENSE_VALUES: set[str] = {
    "CC0",
    "CC-BY",
    "CC-BY-SA",
    "PUBLIC_DOMAIN",
    "OTHER_FREE",
    "UNKNOWN",
    "RESTRICTED",
}


def _fields(model: type[Any]) -> set[str]:
    return set(model.model_fields.keys())


def test_video_record_schema_snapshot() -> None:
    missing = VIDEO_RECORD_REQUIRED_FIELDS - _fields(VideoRecord)
    assert not missing, (
        f"VideoRecord lost required fields: {sorted(missing)}. "
        "Update db_structured.md and this snapshot together."
    )


def test_provenance_schema_snapshot() -> None:
    missing = PROVENANCE_REQUIRED_FIELDS - _fields(Provenance)
    assert not missing, f"Provenance lost required fields: {sorted(missing)}"


def test_source_query_schema_snapshot() -> None:
    missing = SOURCE_QUERY_REQUIRED_FIELDS - _fields(SourceQuery)
    assert not missing, f"SourceQuery lost required fields: {sorted(missing)}"


def test_benchmark_result_schema_snapshot() -> None:
    missing = BENCHMARK_RESULT_REQUIRED_FIELDS - _fields(BenchmarkResult)
    assert not missing, (
        f"BenchmarkResult lost required fields: {sorted(missing)}. "
        "Downstream reports/*.json consumers will break."
    )


def test_license_enum_snapshot() -> None:
    actual = {member.value for member in License}
    missing = REQUIRED_LICENSE_VALUES - actual
    assert not missing, (
        f"License enum lost required values: {sorted(missing)}. "
        "db_structured.md documents these as the license taxonomy."
    )
    for value in ("CC0", "CC-BY", "CC-BY-SA", "PUBLIC_DOMAIN", "OTHER_FREE"):
        member = License(value)
        assert member.is_redistributable, (
            f"License.{member.name} must remain in the redistributable set; "
            "changing this silently would corrupt downstream training corpora."
        )
    assert not License.UNKNOWN.is_redistributable
    assert not License.RESTRICTED.is_redistributable


def test_source_query_serialization_format_snapshot() -> None:
    q = SourceQuery(terms=["a", "b"], max_results=3, language="en")
    assert q.serialize() == "terms=a|b;max=3;lang=en"
    q2 = SourceQuery(terms=[], max_results=1)
    assert q2.serialize() == "terms=;max=1;lang="
