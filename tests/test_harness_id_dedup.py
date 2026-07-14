"""Documents the current state of intra-source ID deduplication.

Passing test: the fixtures we ship do not contain duplicate IDs within
a single source (a sanity check on the fixture curation itself).

`xfail` test: `run_comparison` does not currently collapse duplicate IDs
within a single source. When Coding-Agent adds that guard (P0 in
`docs/plan-2026-07-14.md`), flip the xfail to a hard assert.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.records import SourceQuery, VideoRecord
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _wikimedia_records() -> list[VideoRecord]:
    query = SourceQuery(terms=["pasta"], max_results=25)
    return WikimediaCommonsSource().parse(
        json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
    )


def test_fixture_wikimedia_has_no_duplicate_ids() -> None:
    records = _wikimedia_records()
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids)), f"fixture duplicates: {ids}"


@pytest.mark.xfail(
    reason="P0 in plan-2026-07-14: run_comparison does not yet dedup by VideoRecord.id",
    strict=False,
)
def test_run_comparison_dedups_duplicate_ids_within_source() -> None:
    records = _wikimedia_records()
    duplicated = records + records  # each record appears twice
    rows = run_comparison(
        SourceQuery(terms=["pasta"], max_results=25),
        {"wikimedia": duplicated},
        notes="dedup-probe",
    )
    row = next(r for r in rows if r.source == "wikimedia")
    assert row.n_records == len(records), (
        f"expected dedup down to {len(records)}, got {row.n_records}"
    )
