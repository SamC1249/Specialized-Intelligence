from specint.compare.ablation import PRESETS, ablate, to_report
from specint.compare.dedup import DedupResult, dedup_key, dedupe
from specint.compare.fixtures import default_fixtures_dir, load_fixture_by_source
from specint.compare.harness import aggregate, run_comparison

__all__ = [
    "PRESETS",
    "DedupResult",
    "ablate",
    "aggregate",
    "dedup_key",
    "dedupe",
    "default_fixtures_dir",
    "load_fixture_by_source",
    "run_comparison",
    "to_report",
]
