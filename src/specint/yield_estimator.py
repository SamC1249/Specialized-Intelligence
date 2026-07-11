"""Yield estimator — how many license-clean hours can each source deliver?

We derive yield from the *listing-level* metadata each API surfaces
(the ``total`` counter that comes back with any search response), so we
can rank sources without downloading any media. This is the H1
question restated: "How many hours per crawl-day per source?".

Estimator inputs are:
  - Total upstream match count (from a listing response).
  - License-clean rate observed on a per-source sample.
  - Mean declared duration on the sample.

The estimator prefers to *under-count* — for sources like YouTube where
we can't redistribute media, we still report the *URL* yield but the
"redistributable hours" contribution is 0.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from specint.records import License, VideoRecord


@dataclass(frozen=True)
class YieldEstimate:
    source: str
    upstream_total: int
    sample_size: int
    license_clean_rate: float
    mean_duration_s: float
    est_records: int
    est_license_clean_records: int
    est_hours_landing_pages: float
    est_hours_redistributable: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "upstream_total": self.upstream_total,
            "sample_size": self.sample_size,
            "license_clean_rate": round(self.license_clean_rate, 4),
            "mean_duration_s": round(self.mean_duration_s, 2),
            "est_records": self.est_records,
            "est_license_clean_records": self.est_license_clean_records,
            "est_hours_landing_pages": round(self.est_hours_landing_pages, 2),
            "est_hours_redistributable": round(self.est_hours_redistributable, 2),
        }


LISTING_TOTAL_PATHS: dict[str, tuple[str, ...]] = {
    "wikimedia": ("query", "searchinfo", "totalhits"),
    "archive_org": ("response", "numFound"),
    "peertube": ("total",),
    "youtube": ("pageInfo", "totalResults"),
}


def extract_listing_total(source: str, raw: Any) -> int | None:
    """Walk the well-known JSON path for `source` and return the total.

    Returns ``None`` when the payload doesn't contain the expected keys.
    """
    path = LISTING_TOTAL_PATHS.get(source)
    if not path or not isinstance(raw, dict):
        return None
    cur: Any = raw
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    if isinstance(cur, bool):
        return None
    if isinstance(cur, int | float):
        return int(cur)
    if isinstance(cur, str) and cur.isdigit():
        return int(cur)
    return None


def _redistributable(record: VideoRecord) -> bool:
    return record.license is not License.UNKNOWN and record.license.is_redistributable


def estimate_yield(
    source: str,
    sample: Iterable[VideoRecord],
    upstream_total: int | None,
) -> YieldEstimate:
    sample_list = list(sample)
    sample_size = len(sample_list)
    if sample_size == 0:
        return YieldEstimate(
            source=source,
            upstream_total=upstream_total or 0,
            sample_size=0,
            license_clean_rate=0.0,
            mean_duration_s=0.0,
            est_records=upstream_total or 0,
            est_license_clean_records=0,
            est_hours_landing_pages=0.0,
            est_hours_redistributable=0.0,
        )

    clean_count = sum(1 for r in sample_list if _redistributable(r))
    license_clean_rate = clean_count / sample_size
    durations = [r.duration_s for r in sample_list if r.duration_s]
    mean_duration_s = float(sum(durations) / len(durations)) if durations else 0.0

    est_records = upstream_total if upstream_total is not None else sample_size
    est_license_clean = round(est_records * license_clean_rate)
    est_hours_landing = est_records * mean_duration_s / 3600.0
    est_hours_redist = est_license_clean * mean_duration_s / 3600.0

    if source == "youtube":
        est_hours_redist = 0.0

    return YieldEstimate(
        source=source,
        upstream_total=int(upstream_total or sample_size),
        sample_size=sample_size,
        license_clean_rate=license_clean_rate,
        mean_duration_s=mean_duration_s,
        est_records=int(est_records),
        est_license_clean_records=int(est_license_clean),
        est_hours_landing_pages=float(est_hours_landing),
        est_hours_redistributable=float(est_hours_redist),
    )
