from specint.compare.dedup import DedupReport, dedup_records
from specint.compare.diff import DiffRow, diff_reports
from specint.compare.fixture_provider import (
    FIXTURE_MANIFEST,
    load_records_by_source,
    load_suite,
)
from specint.compare.harness import aggregate, run_comparison, run_matrix

__all__ = [
    "FIXTURE_MANIFEST",
    "DedupReport",
    "DiffRow",
    "aggregate",
    "dedup_records",
    "diff_reports",
    "load_records_by_source",
    "load_suite",
    "run_comparison",
    "run_matrix",
]
