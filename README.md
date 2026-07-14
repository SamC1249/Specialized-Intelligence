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

# Offline comparison against checked-in fixtures (no network):
python -m specint compare --fixtures --fixtures-dir tests/fixtures \
  --scorer v2 --dedup --terms cooking recipe \
  --output reports/example.json

# Multi-query benchmark (H1: reduce single-query variance):
python -m specint matrix --suite tests/fixtures/suite/query_suite.json \
  --fixtures-dir tests/fixtures --scorer v2 --dedup \
  --output reports/matrix.json

# A/B compare scorer v1 vs v2 on the same fixtures (H2):
python -m specint scorer-compare --fixtures-dir tests/fixtures \
  --dedup --output reports/scorer.json

# Mechanical report diff (regression gate):
python -m specint diff reports/baseline-2026-06-20.json reports/example.json

# Live comparison (only with explicit opt-in):
SPECINT_RUN_INTEGRATION=1 python -m specint compare --terms cooking
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
| `src/specint/quality/`          | Metadata-only quality scorers.                        |
| `src/specint/compare/`          | Systematic benchmark harness.                         |
| `src/specint/cli.py`            | `python -m specint`.                                  |
| `tests/`                        | Offline-only pytest suite + fixtures.                 |
| `.github/workflows/ci.yml`      | Lint, types, unit, e2e-fixture tests.                 |

## License & contribution

MIT for code. See `AGENTS.md` for the agent collaboration loop and
`docs/plan-2026-06-20.md` for the seed research plan.
