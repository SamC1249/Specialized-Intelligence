"""Adversarial provenance-completeness test.

Every parsed `VideoRecord` must carry non-empty provenance. Missing
provenance is silent training-set contamination: we would not know
which extractor produced the record and could not re-run at the same
commit hash. This test iterates all adapters and asserts:

- `provenance.extractor` names a real module we import.
- `provenance.query` is a non-empty serialized `SourceQuery`.
- `provenance.fetched_at` is timezone-aware and UTC.

It uses the same audit-spec table as the license audit so adding a new
source in one place enrolls it in both.
"""

from __future__ import annotations

import importlib
from datetime import UTC
from pathlib import Path

import pytest

from specint.records import SourceQuery
from tests.test_adversarial_license_audit import _AUDIT_SPECS


@pytest.mark.parametrize("spec", _AUDIT_SPECS, ids=lambda s: s.slug)
def test_provenance_is_present_and_utc(fixtures_dir: Path, spec) -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    records = spec.build(fixtures_dir, query)
    assert records, f"{spec.slug}: fixture must produce at least one record"

    for r in records:
        prov = r.provenance
        assert prov.extractor, f"{spec.slug}: {r.id} has empty provenance.extractor"

        try:
            importlib.import_module(prov.extractor)
        except ImportError as exc:  # pragma: no cover - defensive
            pytest.fail(
                f"{spec.slug}: {r.id} provenance.extractor={prov.extractor!r} "
                f"is not an importable module ({exc})."
            )

        assert prov.query, f"{spec.slug}: {r.id} has empty provenance.query"
        assert "terms=" in prov.query, (
            f"{spec.slug}: {r.id} provenance.query {prov.query!r} does not match "
            "SourceQuery.serialize() format"
        )

        assert prov.fetched_at.tzinfo is not None, (
            f"{spec.slug}: {r.id} provenance.fetched_at is naive; must be tz-aware UTC"
        )
        assert prov.fetched_at.utcoffset() is not None
        assert prov.fetched_at.utcoffset() == UTC.utcoffset(prov.fetched_at), (
            f"{spec.slug}: {r.id} provenance.fetched_at is not UTC ({prov.fetched_at.tzinfo})"
        )
