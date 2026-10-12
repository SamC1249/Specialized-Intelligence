"""Deterministic diff between two `BenchmarkResult` reports.

Addresses adversarial question #4 from the plans: before anyone can
claim "we got better", a byte-reproducible diff of two
`BenchmarkResult` payloads must exist. Both inputs are expected to be
JSON payloads emitted by `specint.cli._cmd_compare` (shape:
`{"query": {...}, "rows": [BenchmarkResult, ...]}`).

Output shape:

    {
      "query": {"a": {...}, "b": {...}},
      "sources": [
        {
          "source": "wikimedia",
          "delta": {"n_records": +3, "mean_quality": +0.07, ...},
          "a": {...},
          "b": {...}
        },
        ...
      ],
      "added_sources":   ["youtube_cc"],
      "removed_sources": [],
    }

Rows are sorted by source name so the output is diff-friendly in git.
"""

from __future__ import annotations

from typing import Any

_NUMERIC_FIELDS: tuple[str, ...] = (
    "n_records",
    "n_license_clean",
    "total_duration_s",
    "mean_quality",
    "p50_quality",
    "p90_quality",
    "unique_authors",
)


def _index_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("rows") or []
    return {row["source"]: row for row in rows if isinstance(row, dict) and "source" in row}


def _delta(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for field in _NUMERIC_FIELDS:
        va = float((a or {}).get(field) or 0.0)
        vb = float((b or {}).get(field) or 0.0)
        out[field] = round(vb - va, 6)
    return out


def diff_reports(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_rows = _index_rows(a)
    b_rows = _index_rows(b)

    sources_in_both = sorted(set(a_rows) & set(b_rows))
    added = sorted(set(b_rows) - set(a_rows))
    removed = sorted(set(a_rows) - set(b_rows))

    sources_block: list[dict[str, Any]] = []
    for src in sources_in_both:
        sources_block.append(
            {
                "source": src,
                "delta": _delta(a_rows[src], b_rows[src]),
                "a": a_rows[src],
                "b": b_rows[src],
            }
        )
    for src in added:
        sources_block.append(
            {
                "source": src,
                "delta": _delta(None, b_rows[src]),
                "a": None,
                "b": b_rows[src],
            }
        )
    for src in removed:
        sources_block.append(
            {
                "source": src,
                "delta": _delta(a_rows[src], None),
                "a": a_rows[src],
                "b": None,
            }
        )

    return {
        "query": {"a": a.get("query"), "b": b.get("query")},
        "sources": sources_block,
        "added_sources": added,
        "removed_sources": removed,
    }
