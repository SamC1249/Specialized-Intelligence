"""Pipeline stages that operate on `VideoRecord` collections.

Sources produce records; the pipeline transforms them (dedup, later
also decontamination, gating, sampling). Each stage is a pure function
so we can test them offline with fixtures.
"""

from __future__ import annotations

from specint.pipeline.dedup import DedupResult, dedup_records

__all__ = ["DedupResult", "dedup_records"]
