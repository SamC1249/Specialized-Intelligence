# AGENTS.md

This repository, **Specialized-Intelligence**, is a research-engineering project
whose goal is to discover and assemble **internet-scale, legally-clean,
frontier-quality data** for training video world models. The first vertical we
are pushing on is **cooking videos** (long-horizon, procedural, multi-step,
state-rich, contact-rich), because it is one of the hardest and most
information-dense slices of human activity that is widely captured on the
public web.

This file is the single source of truth for any agent (human or AI) operating
in the repo. Read it first.

---

## 1. The Mission

Build a reproducible, defensible pipeline that, for any chosen target domain
(starting with cooking), can:

1. **Discover** every legally re-usable long-form video on the public internet
   that depicts the target activity.
2. **Acquire** the raw video + side-channels (audio, ASR, comments, metadata)
   under terms that allow research training and republication.
3. **Curate** it down to the *highest-quality* slice — high motion, low ad
   pollution, recipe-grounded, low duplication, broad demographic and
   geographic coverage.
4. **Annotate** it with structured, temporally grounded labels (procedural
   steps, ingredients, tools, object states, hand-object contact, camera
   pose, recipe outcome).
5. **Evaluate** the resulting dataset against frontier world-model benchmarks
   (WorldModelBench, MBench, HD-EPIC VQA, Ego2World) and against custom
   adversarial probes.
6. **Ship** it (manifests, embeddings, captions, license trail) so that
   anyone can reproduce the pipeline without paying for data or breaking
   terms of service.

Constraints, ranked by hardness:

- **Legal**: never violate platform ToS, never redistribute copyrighted video
  bytes, never pay for data. Prefer CC-BY / CC0 / public-domain sources, and
  ID-only manifests for anything else.
- **Frontier**: every design choice has to be defensible against the state of
  the art (NVIDIA Cosmos, DreamDojo, HD-EPIC, OmniWorld, DenseStep2M).
- **Systematic**: zero one-off scripts; everything is a configurable
  pipeline stage with a test.
- **Robust**: deduplicated, contamination-checked, license-audited, with a
  data-card emitted on every shard.

## 2. The Agents

The project is operated by named LLM agents, each with a single role and a
distinct identity in `plan.md`. New agents must be added here before they
write to the repo.

| Identity              | Role                                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `Adversarial-Agent`   | Daily adversarial review of plans + code. Surfaces failure modes, contamination, legal risk, blind spots. Writes plans into `docs/plan/<date>.md` and research notes into `docs/artifacts/`. Runs on a cron schedule. |
| `Implementer-Agent`   | (reserved) Picks the top item from the latest plan and lands a vertical slice of code + tests. |
| `Curator-Agent`       | (reserved) Owns the data-curation pipeline stages and their configs. |
| `Eval-Agent`          | (reserved) Owns benchmarks, golden sets, regression suites. |

Every agent **must**:

- Sign each `plan.md` summary with `(Adversarial-Agent, 2026-06-23 17:42 UTC)`
  style attribution.
- Write to its own branch (`cursor/<short-slug>-<id>`).
- Open a PR; never push to `main` directly.
- Update `db_structured.md` if it adds, removes, or renames any data table,
  pipeline stage, or external API. This is enforced by a CI check.
- Update `AGENTS.md` if it adds a new agent identity.

## 3. Repository Layout

```
.
├── AGENTS.md                # this file
├── README.md
├── db_structured.md         # single source of truth for data + APIs
├── plan.md                  # rolling log of 1-2 line daily summaries
├── docs/
│   ├── plan/                # one detailed plan per UTC day, named YYYY-MM-DD.md
│   └── artifacts/           # research notes, paper summaries, design docs
├── src/
│   └── specialized_intelligence/
│       ├── __init__.py
│       ├── sources/         # source discovery (CC search, Vimeo, PeerTube, archive.org)
│       ├── acquire/         # licence-aware download + manifest emission
│       ├── curate/          # split, filter, dedup, caption stages
│       ├── annotate/        # procedural step / object-state annotators
│       ├── eval/            # benchmark adapters and adversarial probes
│       └── cli.py
├── tests/
│   ├── unit/                # pure-Python unit tests, no network, no GPU
│   └── e2e/                 # end-to-end on a tiny fixture corpus
├── scripts/                 # one-shot dev scripts, never imported
├── .github/workflows/       # CI: lint, type, unit, e2e, license-audit
└── .pre-commit-config.yaml
```

## 4. Coding Conventions

- Python 3.11+. Use `ruff` (lint + format) and `pyright` (types).
- Max **800 lines per file**. If you cross it, split.
- Every public function declares its input/output types and units (e.g.
  `seconds`, `frames`, `bytes`).
- No silent network calls in unit tests. Use fixtures or `respx`.
- No global mutable state.
- Configuration is YAML in `configs/`, loaded with `pydantic-settings`.
- Reusable UI components go in `/components` (frontend, not yet created).

## 5. Definition of Done for any change

A PR is mergeable when:

1. `pre-commit run --all-files` is clean.
2. `pytest tests/unit -q` passes.
3. `pytest tests/e2e -q -m "not slow"` passes on the fixture corpus.
4. `docs/plan/<today>.md` (if a plan was produced) or `docs/artifacts/`
   (if research was produced) has been updated.
5. `db_structured.md` is in sync with the code if any data shape changed.
6. `plan.md` has a one-or-two-line entry signed by the responsible agent.

## 6. Non-goals

- We do **not** build a model. We only build the data + the evaluation that
  proves the data is frontier-grade.
- We do **not** scrape behind authentication, evade rate limits, or use
  residential proxies. The pipeline must run from a single IP at human
  speeds and still hit scale, via federation and prioritisation.
- We do **not** pay for data, period.
