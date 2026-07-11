# Specialized-Intelligence

Internet-scale, **legally sourced** video data collection for frontier
world models. Today's narrow target: **cooking videos**.

## Why this repo exists

Frontier video models need long, procedural, multi-object footage with
reversible-vs-irreversible state changes. Cooking is the cleanest such
domain on the open web — but the obvious source (mainstream YouTube
channels) is mostly all-rights-reserved. This repo systematically
discovers, scores, and *compares* legally permissive sources so we can
build training corpora without paying or violating ToS.

## Quickstart

```bash
python -m pip install -e ".[dev]"
pre-commit install
pytest -q

# Offline comparison harness (no network):
python -m specint compare --fixtures --terms cooking recipe \
  --output reports/example.json

# Head-to-head scorer benchmark (v1 vs v2), offline:
python -m specint compare --fixtures --head-to-head \
  --output reports/scorers.json

# License-clean yield estimate from listing totals, offline:
python -m specint yield --fixtures-dir tests/fixtures \
  --output reports/yield.json

# Multilingual seed-term expansion (fr + es cooking corpora):
python -m specint compare --fixtures --languages fr es \
  --output reports/multilang.json

# Live comparison (only with explicit opt-in):
SPECINT_RUN_INTEGRATION=1 python -m specint compare --terms cooking

# Live integration test suite (skipped by default):
SPECINT_RUN_INTEGRATION=1 pytest -q -m integration
```

## Layout

| Path                            | Role                                                  |
| ------------------------------- | ----------------------------------------------------- |
| `AGENTS.md`                     | Operating contract for AI agents on this repo.        |
| `plan.md`                       | One-line dated summaries (newest on top).             |
| `docs/plan-YYYY-MM-DD.md`       | Adversarial-Agent's daily plan / hypothesis.          |
| `db_structured.md`              | Canonical schemas (single source of truth).           |
| `src/specint/records.py`        | Pydantic models matching `db_structured.md`.          |
| `src/specint/sources/`          | Per-upstream adapters (BaseSource subclasses).        |
| `src/specint/quality/`          | Metadata-only quality scorers (`v1`, `v2`).           |
| `src/specint/compare/`          | Systematic benchmark harness (head-to-head).          |
| `src/specint/pipeline/`         | Post-collection dedup + join filters.                 |
| `src/specint/yield_estimator.py`| Legal-yield projections from listing totals.          |
| `src/specint/cli.py`            | `python -m specint {sources,compare,yield,...}`.      |
| `tests/`                        | Offline pytest suite + fixtures.                      |
| `tests/integration/`            | Live network suite, gated by env var.                 |
| `.github/workflows/ci.yml`      | Lint, types, unit, e2e-fixture tests.                 |

## License & contribution

MIT for code. See `AGENTS.md` for the agent collaboration loop and
`docs/plan-2026-06-20.md` for the seed research plan.
