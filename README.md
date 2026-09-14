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

# Domain profiles cover multiple domains + languages out of the box:
python -m specint domains
python -m specint compare --fixtures --domain cooking --language fr \
  --output reports/example-fr.json

# Diff any two reports per source (candidate - baseline):
python -m specint compare-diff \
  --baseline reports/baseline-2026-06-20.json \
  --candidate reports/compare-2026-09-14.json \
  --output reports/diff-2026-09-14.json

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
| `src/specint/licenses.py`       | Central license URL/short-name classifier.            |
| `src/specint/language.py`       | Dependency-free BCP-47 detection (signal-only).       |
| `src/specint/domains.py`        | Multilingual seed-term registry (cooking, surgery, ...) |
| `src/specint/cli.py`            | `python -m specint`.                                  |
| `tests/`                        | Offline-only pytest suite + fixtures.                 |
| `.github/workflows/ci.yml`      | Lint, types, unit, e2e-fixture tests.                 |

## License & contribution

MIT for code. See `AGENTS.md` for the agent collaboration loop and
`docs/plan-2026-06-20.md` for the seed research plan.
