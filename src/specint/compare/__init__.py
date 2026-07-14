from specint.compare.dedup import dedupe_records, normalize_title, normalize_url
from specint.compare.diff import DiffRow, diff_reports
from specint.compare.harness import aggregate, run_comparison, run_matrix

__all__ = [
    "DiffRow",
    "aggregate",
    "dedupe_records",
    "diff_reports",
    "normalize_title",
    "normalize_url",
    "run_comparison",
    "run_matrix",
]
