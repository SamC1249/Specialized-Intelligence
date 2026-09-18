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

# Multilingual seed terms (English, Spanish, French, German, Italian, Portuguese, Dutch):
python -m specint compare --fixtures --lang es --output reports/example-es.json

# Regression-check today's run against a committed baseline:
python -m specint compare-diff \
  reports/baseline-2026-09-18.json reports/example.json --strict

# Live comparison (only with explicit opt-in):
SPECINT_RUN_INTEGRATION=1 python -m specint compare --terms cooking

# YouTube CC-BY listings additionally require:
YOUTUBE_API_KEY=... SPECINT_RUN_INTEGRATION=1 \
  python -m specint compare --only youtube_cc --terms cooking
```

## Registered sources

| slug          | licenses accepted                    | media?    |
| ------------- | ------------------------------------ | --------- |
| `wikimedia`   | CC0 / CC-BY / CC-BY-SA / PD          | yes       |
| `archive_org` | CC family / PD (per-item)            | yes       |
| `peertube`    | CC-BY / CC-BY-SA / CC0 (per-item)    | yes       |
| `common_crawl`| Page-level `rel="license"` only      | url only  |
| `youtube_cc`  | CC-BY (only if `status.license=creativeCommon`) | url only |

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
