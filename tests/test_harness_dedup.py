"""Dedup expectations for the comparison harness.

Motivation: the same Wikimedia video mirrored on Internet Archive
(or Common Crawl) currently contributes to `__total__` twice, which
inflates every `n_records`, `total_duration_s`, and `unique_authors`
count. See `docs/artifacts/2026-09-11-mlt-dedup-maze.md` for context.

We check two invariants:

  1. If two records share the same `id`, `__total__` must not
     double-count them. (Currently *expected to fail* — flip xfail off
     once URL-canonical dedup lands in the harness.)

  2. Even without dedup, `n_license_clean <= n_records` and
     `unique_authors <= n_records` must hold for every row. This is
     already true today; the test guards against a regression when
     dedup is added.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.compare import run_comparison
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(source: str, native_id: str, *, license_: License = License.CC0) -> VideoRecord:
    prov = Provenance(extractor=f"test.{source}", fetched_at=datetime.now(UTC), query="")
    return VideoRecord(
        id=f"canonical:{native_id}",
        source=source,
        source_native_id=native_id,
        url=f"https://example.test/{source}/{native_id}",
        title=f"{source} record {native_id}",
        license=license_,
        duration_s=60.0,
        height=720,
        author=f"author-{native_id}",
        provenance=prov,
    )


def test_row_invariants_hold_for_every_source() -> None:
    query = SourceQuery(terms=["cooking"])
    by_source = {
        "wikimedia": [_rec("wikimedia", "1"), _rec("wikimedia", "2")],
        "archive_org": [_rec("archive_org", "3", license_=License.UNKNOWN)],
    }
    rows = run_comparison(query, by_source, notes="invariants")
    for row in rows:
        assert row.n_license_clean <= row.n_records
        assert row.unique_authors <= row.n_records
        assert 0.0 <= row.mean_quality <= 1.0
        assert 0.0 <= row.p50_quality <= 1.0
        assert 0.0 <= row.p90_quality <= 1.0


@pytest.mark.xfail(
    reason="Cross-source dedup not implemented yet; see plan-2026-09-11 H1/H2.",
    strict=True,
)
def test_total_row_deduplicates_by_canonical_id() -> None:
    query = SourceQuery(terms=["cooking"])
    dup_native = "shared-video"
    by_source = {
        "wikimedia": [_rec("wikimedia", dup_native)],
        "archive_org": [_rec("archive_org", dup_native)],
    }
    rows = run_comparison(query, by_source, notes="dedup")
    total = next(r for r in rows if r.source == "__total__")
    per_source_records = sum(r.n_records for r in rows if r.source != "__total__")
    assert per_source_records == 2, "sanity check on setup"
    assert total.n_records == 1, (
        "`__total__` must collapse records that share the same canonical id"
    )
