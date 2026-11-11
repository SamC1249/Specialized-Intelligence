"""Per-source yield estimator (metadata-only).

Given, for each source, (a) the upstream "total hits" the listing API
claims and (b) the records we actually parsed into license-clean
`VideoRecord`s, this module emits a deterministic, JSON-serializable
`YieldEstimate` table so we can rank sources by order-of-magnitude
yield without downloading a single video frame.

We deliberately separate three numbers:

  * `upstream_total_hits`     — what the API says it has for the query.
    Many APIs cap listing counts (e.g. Archive.org returns at most
    10 000). Numbers above `UPSTREAM_CENSOR_THRESHOLD` are reported
    with `censored=True` so no one mistakes the cap for a true count.
  * `records_parsed`          — records our adapter produced.
  * `records_license_clean`   — subset of the above with a
    redistributable license (CC0/CC-BY/CC-BY-SA/PD/OTHER_FREE).

The yield *rate* is `records_license_clean / records_parsed` (0 when
`records_parsed == 0`), and the *projected daily yield* extrapolates it
to a hypothetical crawl-day budget of `CRAWL_DAY_LIST_CALLS` listing
calls at the current per-call batch size.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict

from specint.records import VideoRecord

UPSTREAM_CENSOR_THRESHOLD = 10_000
CRAWL_DAY_LIST_CALLS = 2_000


class YieldEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    upstream_total_hits: int
    records_parsed: int
    records_license_clean: int
    license_clean_rate: float
    censored: bool
    projected_daily_records: int
    notes: str = ""


def estimate(
    source: str,
    upstream_total_hits: int,
    records: Iterable[VideoRecord],
    batch_size: int = 50,
    notes: str = "",
) -> YieldEstimate:
    items = list(records)
    parsed = len(items)
    license_clean = sum(1 for r in items if r.license.is_redistributable)
    rate = (license_clean / parsed) if parsed else 0.0
    censored = upstream_total_hits >= UPSTREAM_CENSOR_THRESHOLD
    per_call = batch_size if batch_size > 0 else max(parsed, 1)
    projected = round(CRAWL_DAY_LIST_CALLS * per_call * rate)
    return YieldEstimate(
        source=source,
        upstream_total_hits=int(upstream_total_hits),
        records_parsed=parsed,
        records_license_clean=license_clean,
        license_clean_rate=rate,
        censored=censored,
        projected_daily_records=projected,
        notes=notes,
    )


def to_rows(estimates: Iterable[YieldEstimate]) -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in estimates]


__all__ = [
    "CRAWL_DAY_LIST_CALLS",
    "UPSTREAM_CENSOR_THRESHOLD",
    "YieldEstimate",
    "estimate",
    "to_rows",
]
