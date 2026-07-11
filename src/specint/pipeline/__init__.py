"""Post-collection pipeline utilities (dedup, filters, joins)."""

from specint.pipeline.dedup import DedupStats, dedupe

__all__ = ["DedupStats", "dedupe"]
