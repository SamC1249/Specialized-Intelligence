"""Ablation harness.

`run_comparison` produces one BenchmarkResult per source under a single
quality-scoring configuration. An adversarial reviewer can (rightly)
point out that any single ranking is a function of *our chosen
weights*, and might not survive a different weighting.

`run_ablation` re-runs the harness across a list of `WeightConfig`s and
emits a compact table that shows the source ranking under each config,
plus the mean-quality delta versus the default.

Output shape (JSON-serialisable):

    {
      "configs": ["default", "license-only", ...],
      "sources": ["archive_org", "common_crawl", ...],
      "rankings": {
        "default": [
          {"source": "wikimedia", "mean_quality": 0.62, "rank": 1},
          ...
        ],
        ...
      },
      "delta_vs_default": {
        "license-only": {"wikimedia": +0.03, ...},
        ...
      }
    }
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from specint.quality.metrics import DEFAULT_WEIGHTS, WeightConfig, score_records
from specint.records import SourceQuery, VideoRecord


@dataclass(frozen=True)
class AblationRow:
    config: str
    source: str
    n_records: int
    mean_quality: float
    rank: int


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _rank_sources(scored_by_source: Mapping[str, list[VideoRecord]]) -> list[tuple[str, float]]:
    means = [
        (src, _mean([r.quality_score or 0.0 for r in recs]))
        for src, recs in scored_by_source.items()
        if recs
    ]
    return sorted(means, key=lambda pair: (-pair[1], pair[0]))


def default_configs() -> list[WeightConfig]:
    """Standard ablation set. Any additions should be justified in a plan."""
    return [
        WeightConfig(name="default", weights=DEFAULT_WEIGHTS),
        WeightConfig(
            name="license-only",
            weights={"license_clean": 1.0},
        ),
        WeightConfig(
            name="proc-only",
            weights={"procedural_density": 1.0, "has_steps": 0.0},
        ),
        WeightConfig(
            name="no-license",
            weights={
                "duration": 0.15,
                "resolution": 0.25,
                "text_density": 0.15,
                "has_steps": 0.10,
                "procedural_density": 0.20,
                "cooking_relevance": 0.15,
            },
        ),
        WeightConfig(
            name="multilingual-heavy",
            weights={
                "license_clean": 0.25,
                "cooking_relevance": 0.35,
                "procedural_density": 0.20,
                "resolution": 0.10,
                "text_density": 0.10,
            },
        ),
    ]


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    configs: Iterable[WeightConfig] | None = None,
) -> dict[str, Any]:
    configs_list = list(configs) if configs is not None else default_configs()
    if not configs_list:
        raise ValueError("ablation requires at least one WeightConfig")

    sources = sorted(by_source.keys())
    rankings: dict[str, list[dict[str, Any]]] = {}
    means_by_config: dict[str, dict[str, float]] = {}

    for cfg in configs_list:
        scored_by_source: dict[str, list[VideoRecord]] = {
            src: score_records(records, weights=cfg.weights) for src, records in by_source.items()
        }
        ranked = _rank_sources(scored_by_source)
        rows = [
            AblationRow(
                config=cfg.name,
                source=src,
                n_records=len(scored_by_source[src]),
                mean_quality=round(mean, 6),
                rank=i + 1,
            )
            for i, (src, mean) in enumerate(ranked)
        ]
        rankings[cfg.name] = [
            {
                "source": row.source,
                "rank": row.rank,
                "mean_quality": row.mean_quality,
                "n_records": row.n_records,
            }
            for row in rows
        ]
        means_by_config[cfg.name] = {src: mean for src, mean in ranked}

    default_means = means_by_config.get("default", {})
    delta_vs_default: dict[str, dict[str, float]] = {}
    for cfg_name, means in means_by_config.items():
        if cfg_name == "default":
            continue
        delta_vs_default[cfg_name] = {
            src: round(means.get(src, 0.0) - default_means.get(src, 0.0), 6) for src in sources
        }

    return {
        "query": query.model_dump(mode="json"),
        "configs": [cfg.name for cfg in configs_list],
        "sources": sources,
        "rankings": rankings,
        "delta_vs_default": delta_vs_default,
    }
