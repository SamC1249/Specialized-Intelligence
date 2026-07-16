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
  --scorer v1 --output reports/example.json

# A/B a new scorer against v1 on the same fixtures:
python -m specint compare --fixtures --scorer v2 \
  --output reports/example-v2.json
python -m specint diff reports/example.json reports/example-v2.json \
  --output reports/example-diff.json

# Multi-query benchmark matrix (per-query and per-source aggregates):
python -m specint matrix --fixtures --name cooking-suite \
  --output reports/example-matrix.json

# Live comparison (only with explicit opt-in):
SPECINT_RUN_INTEGRATION=1 python -m specint compare --terms cooking
```

## Comparison-first, not anecdotal

Every new adapter, scorer, or filter must:

- run through `specint.compare.harness.run_comparison` (single query)
  or `run_matrix` (multi-query suite),
- emit a fresh JSON report under `reports/`,
- and be diffable against the previous baseline via
  `python -m specint diff`.

Reports carry the *exact* extractor commit stamp
(`Provenance.extractor_git`) so we can reproduce yesterday's numbers
tomorrow. AGENTS.md rule 2 (provenance is mandatory) is enforced at
model level: `Provenance` defaults `extractor_git` to
`specint._version.get_extractor_git()`, which reads `GITHUB_SHA`,
falls back to `git rev-parse --short=12 HEAD`, and only lands on
`"dev"` when neither is available.

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
