"""Metadata-only yield estimator.

Given a list of `VideoRecord`s per source (typically the parsed output
of a fixture, but works identically on live results), report projected
license-clean yield without downloading any media. This lets us budget
crawl-days against sources rather than spending crawl on saturated ones.

The estimator is deliberately conservative:
  - `hours_license_clean` sums declared durations only for records
    whose `License.is_redistributable` is True.
  - `hours_projected` extrapolates to `projected_pages` API pages by
    (mean license-clean hours per record x projected records).

`projected_pages` defaults to 1 — i.e. "what we already saw" — so
callers who don't want any extrapolation get a straight measurement.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from pydantic import BaseModel, ConfigDict

from specint.records import VideoRecord


class SourceEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    n_records: int
    n_license_clean: int
    hours_license_clean: float
    mean_duration_s: float
    hours_projected: float
    notes: str = ""


class YieldEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceEstimate]
    total_hours_license_clean: float
    total_hours_projected: float


def _clean_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r for r in records if r.license.is_redistributable]


def estimate_source(
    source: str, records: Iterable[VideoRecord], projected_pages: int = 1
) -> SourceEstimate:
    items = list(records)
    clean = _clean_records(items)
    durations = [r.duration_s for r in clean if r.duration_s is not None and r.duration_s > 0]
    hours_clean = sum(durations) / 3600.0 if durations else 0.0
    mean_dur = float(statistics.fmean(durations)) if durations else 0.0
    hours_projected = hours_clean * max(1, projected_pages)
    return SourceEstimate(
        source=source,
        n_records=len(items),
        n_license_clean=len(clean),
        hours_license_clean=hours_clean,
        mean_duration_s=mean_dur,
        hours_projected=hours_projected,
    )


def estimate_yield(
    by_source: Mapping[str, list[VideoRecord]], projected_pages: int = 1
) -> YieldEstimate:
    estimates = [
        estimate_source(src, recs, projected_pages=projected_pages)
        for src, recs in sorted(by_source.items())
    ]
    total_clean = sum(e.hours_license_clean for e in estimates)
    total_proj = sum(e.hours_projected for e in estimates)
    return YieldEstimate(
        sources=estimates,
        total_hours_license_clean=total_clean,
        total_hours_projected=total_proj,
    )
