"""Scoring-profile ablation.

`run_comparison` scores every record under a single profile. This module
runs the harness under every profile in `SCORING_PROFILES` (or a
caller-supplied subset), producing a nested payload:

    {
      "query": {...},
      "profiles": {
          "balanced":         {"rows": [...], "ranking": [...]},
          "license_first":    {"rows": [...], "ranking": [...]},
          "procedural_first": {"rows": [...], "ranking": [...]},
      }
    }

Where `ranking` is the list of source slugs (excluding `__total__`)
sorted by `mean_quality` descending. This is the primitive we use to
answer "does the choice of profile change which source is best?" (H4 in
`docs/plan-2026-09-15.md`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from specint.compare.harness import run_comparison
from specint.quality.metrics import SCORING_PROFILES
from specint.records import BenchmarkResult, SourceQuery, VideoRecord


def _ranking(rows: list[BenchmarkResult]) -> list[str]:
    ranked = [r for r in rows if r.source != "__total__"]
    ranked.sort(key=lambda r: (-r.mean_quality, r.source))
    return [r.source for r in ranked]


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    profiles: Iterable[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    profile_names = list(profiles) if profiles is not None else list(SCORING_PROFILES.keys())
    unknown = [p for p in profile_names if p not in SCORING_PROFILES]
    if unknown:
        raise KeyError(f"unknown profiles: {unknown}; known: {sorted(SCORING_PROFILES)}")

    per_profile: dict[str, dict[str, Any]] = {}
    for name in profile_names:
        rows = run_comparison(query, by_source, notes=notes, profile=name)
        per_profile[name] = {
            "weights": dict(SCORING_PROFILES[name]),
            "rows": [r.model_dump(mode="json") for r in rows],
            "ranking": _ranking(rows),
        }

    rankings = {name: p["ranking"] for name, p in per_profile.items()}
    unique_rankings = {tuple(r) for r in rankings.values()}
    ranking_agreement = len(unique_rankings) == 1

    return {
        "query": query.model_dump(mode="json"),
        "profiles": per_profile,
        "ranking_agreement": ranking_agreement,
        "n_profiles": len(profile_names),
    }
