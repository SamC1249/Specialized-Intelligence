"""Offline yield projections.

Lets us compare the *harvesting power* of two sources without actually
hitting the network. All inputs come from either (a) the terms of a
public API (page size, documented rate limit) or (b) a one-shot
curl we did at design time and wrote into the source adapter's
docstring.

The projection is deliberately conservative: it multiplies the number
of license-clean records per page by the number of pages we could
realistically fetch in a day under the documented rate limit, then
multiplies by the observed mean duration of records in the fixture.
It does **not** try to estimate overlap across sources — that is what
`quality.dedup` is for.
"""

from __future__ import annotations

from dataclasses import dataclass

from specint.records import VideoRecord


@dataclass(frozen=True)
class YieldProjection:
    source: str
    records_per_day: float
    hours_per_day: float
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "records_per_day": round(self.records_per_day, 2),
            "hours_per_day": round(self.hours_per_day, 2),
            "notes": self.notes,
        }


def project_hours_per_day(
    source: str,
    records_per_page: float,
    pages_per_day: float,
    mean_duration_s: float,
    license_clean_fraction: float = 1.0,
    notes: str = "",
) -> YieldProjection:
    """Conservative projection. All inputs are per-source constants.

    Example (Wikimedia Commons):
        records_per_page = 50       # gsrlimit
        pages_per_day    = 480      # 50/min * 60min * 8h sustainable
        mean_duration_s  = 180.0    # observed in the fixture
        license_clean_fraction = 1.0  # Commons is 100% CC-permissive by policy

    This caller is a human (or an adversarial agent) committing a
    conservative set of constants to the repo; the function itself is
    purely arithmetic.
    """
    records_per_page = max(0.0, float(records_per_page))
    pages_per_day = max(0.0, float(pages_per_day))
    mean_duration_s = max(0.0, float(mean_duration_s))
    license_clean_fraction = min(1.0, max(0.0, float(license_clean_fraction)))

    records = records_per_page * pages_per_day * license_clean_fraction
    hours = (records * mean_duration_s) / 3600.0
    return YieldProjection(
        source=source,
        records_per_day=records,
        hours_per_day=hours,
        notes=notes,
    )


def observed_stats(records: list[VideoRecord]) -> tuple[float, float]:
    """Return (mean_duration_s, license_clean_fraction) over `records`.

    Treats `duration_s is None` as missing (dropped from the mean). An
    empty input returns (0.0, 0.0) so callers can safely feed small
    fixtures.
    """
    if not records:
        return (0.0, 0.0)
    durations = [r.duration_s for r in records if r.duration_s is not None and r.duration_s > 0]
    mean_dur = sum(durations) / len(durations) if durations else 0.0
    clean = sum(1 for r in records if r.license.is_redistributable) / len(records)
    return (mean_dur, clean)
