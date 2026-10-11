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

# Offline comparison harness (no network, uses shipped sample fixtures):
python -m specint compare --fixtures --language en \
  --output reports/example.json

# Diff two reports to see per-source deltas (CI/PR friendly):
python -m specint diff reports/baseline-2026-06-20.json reports/baseline-2026-10-11.json

# Multilingual seed term sets:
python -m specint languages

# Live comparison (only with explicit opt-in):
SPECINT_RUN_INTEGRATION=1 python -m specint compare --terms cooking
```

## Current baseline — `reports/baseline-2026-10-11.json`

| source        | n_records | license-clean | license-clean hours | mean quality |
| ------------- | --------- | ------------- | ------------------- | ------------ |
| archive_org   | 3         | 2             | 0.387               | 0.355        |
| common_crawl  | 2         | 1             | 0.103               | 0.630        |
| peertube      | 2         | 2             | 0.228               | 0.569        |
| wikimedia     | 2         | 2             | 0.099               | 0.620        |
| **__total__** | **9**     | **7**         | **0.818**           | **0.522**    |

Any PR touching a source adapter, quality scorer, or dedupe strategy
should re-run `python -m specint compare --fixtures --output <new>` and
include the diff vs this baseline in the PR description.

## Layout

| Path                            | Role                                                  |
| ------------------------------- | ----------------------------------------------------- |
| `AGENTS.md`                     | Operating contract for AI agents on this repo.        |
| `plan.md`                       | One-line dated summaries (newest on top).             |
| `docs/plan-YYYY-MM-DD.md`       | Adversarial-Agent's daily plan / hypothesis.          |
| `db_structured.md`              | Canonical schemas (single source of truth).           |
| `src/specint/records.py`        | Pydantic models matching `db_structured.md`.          |
| `src/specint/sources/`          | Per-upstream adapters (BaseSource subclasses).        |
| `src/specint/quality/`          | Metadata-only quality scorers.                        |
| `src/specint/compare/`          | Systematic benchmark harness.                         |
| `src/specint/cli.py`            | `python -m specint`.                                  |
| `tests/`                        | Offline-only pytest suite + fixtures.                 |
| `.github/workflows/ci.yml`      | Lint, types, unit, e2e-fixture tests.                 |

## License & contribution

MIT for code. See `AGENTS.md` for the agent collaboration loop and
`docs/plan-2026-06-20.md` for the seed research plan.
