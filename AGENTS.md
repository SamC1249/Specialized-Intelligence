# AGENTS.md

This repository's mission: **find internet-wide data for specific frontier
information.** The current focus area is **cooking videos for world models**,
but the research questions are intentionally broad: *what are the most
systematic, robust, and frontier-grade methods to collect the highest quality
video data for difficult problems, legally and at zero or near-zero direct
cost?*

This file is the contract that every collaborating agent (human or AI) must
read before contributing.

## Operating principles

1. **Legality first.** Do not crawl, scrape, or download from sources whose
   Terms of Service forbid it (notably YouTube, regardless of CC tags). Do
   not bypass technological protection measures (TPMs). Maintain
   provenance for every artifact (URL, license, retrieval timestamp,
   transformation lineage). See `docs/artifacts/legal-landscape.md`.
2. **No paid sources.** This is an explicitly free-data effort. If a source
   requires payment or a paid API tier, route the proposal through the
   adversarial review process in `docs/plan/` instead of using it.
3. **Adversarial review by default.** Every dataset proposal is reviewed by
   an adversarial agent (see `docs/plan/`) for: license risk, evaluation
   contamination, bias, provenance gaps, deduplication strategy, and
   world-model utility (not just aesthetic quality).
4. **Single source of truth for data.** All schema, table, and API contracts
   live in `db_structured.md` at the repo root. Update it *before* writing
   any code that touches data.
5. **Reusable components.** UI/data-pipeline primitives go in `components/`
   (or `scripts/` for CLIs) before they show up in app pages. Aim for ~800
   lines per file maximum; split rather than grow.
6. **Typed inputs and outputs.** Before writing a function, declare its
   input/output types and units (frames vs. seconds, RGB vs. BGR, byte vs.
   token). If unclear, write down the question in the relevant plan doc.
7. **Reproducibility.** Every collection job emits a manifest (a JSON Lines
   file with one row per video) that includes hashes, license, source,
   collected-at timestamp, and pipeline version. Manifests, not raw bytes,
   are the canonical artifact.

## Repository layout

```
.
├── AGENTS.md                  # this file
├── README.md
├── plan.md                    # rolling agent log (1-2 line summaries)
├── db_structured.md           # canonical data/API/schema contract
├── docs/
│   ├── plan/<YYYY-MM-DD>.md   # one plan doc per agent-day
│   ├── artifacts/             # paper notes, legal notes, dataset cards
│   └── research/              # longer-form essays / surveys
├── components/                # reusable Python/TS components
├── scripts/                   # standalone CLIs (collection, dedup, etc.)
├── tests/
│   ├── unit/
│   └── e2e/
├── .github/workflows/         # CI pipelines (lint, test, secret scan)
└── .pre-commit-config.yaml    # local pre-commit hooks
```

## Roles

- **Adversarial-Agent**: red-teams every proposal. Writes `docs/plan/*.md`
  and appends a 1-2 line dated entry to `plan.md` after each session.
  Identity tag in commits and plan entries: `Adversarial-Agent`.
- **Builder agents** (future): implement collection, filtering, evaluation
  pipelines. Must respond to every adversarial review comment before
  merging.
- **Reviewer humans**: final arbiter on legal-risk decisions.

## Daily workflow

1. Read `plan.md` and the most recent `docs/plan/<date>.md`.
2. Read `db_structured.md`. If your work changes a schema or contract,
   update this file *first*.
3. Pick or create a todo. Use the agent's todo tooling.
4. Branch from `main`. The current development branch convention is
   `cursor/<topic>-<short-id>`.
5. Run `pre-commit run --all-files` and `pytest -q` before pushing.
6. CI must be green before marking work complete.
7. Append a 1-2 line entry to `plan.md` with `Adversarial-Agent`,
   ISO-8601 finish time (UTC), and commit hash.

## What "frontier video data" means here

Working definition (revisited each cycle): **video corpora that, when used
to pretrain or fine-tune a world model, measurably improve next-frame
prediction, action-conditioned rollout fidelity, and long-horizon temporal
coherence on held-out, license-clean evaluation sets.** Aesthetic quality
is *necessary but not sufficient*; world-model utility is the goal.

## Out of scope (for now)

- Pretraining or fine-tuning models. We focus on the *data flywheel*.
- Hosting/redistributing copyrighted bytes. We index and link, not host.
- Anything that requires bypassing CAPTCHAs, rate limits via IP rotation,
  or downloading via reverse-engineered streaming endpoints.
