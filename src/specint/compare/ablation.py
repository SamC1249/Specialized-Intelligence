"""Cross-profile ablation.

Run the standard comparison harness once per registered quality profile
and emit a flat list of rows tagged by profile, so a reviewer can tell
which heuristic a ranking is actually sensitive to.

Output shape:
  [
    {"profile": "v1",         "source": "wikimedia",   ...},
    {"profile": "v1",         "source": "__total__",   ...},
    {"profile": "v2",         "source": "wikimedia",   ...},
    ...
  ]
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specint.compare.harness import aggregate
from specint.quality import list_profiles, score_records
from specint.records import SourceQuery, VideoRecord


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    profiles: list[str] | None = None,
    notes: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles or list_profiles():
        all_scored: list[VideoRecord] = []
        for source, records in sorted(by_source.items()):
            scored = score_records(records, profile=profile)
            all_scored.extend(scored)
            r = aggregate(source, query.terms, scored, notes=notes)
            rows.append({"profile": profile, **r.model_dump(mode="json")})
        r_total = aggregate("__total__", query.terms, all_scored, notes=notes)
        rows.append({"profile": profile, **r_total.model_dump(mode="json")})
    return rows
