# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Adversarial-Agent @ 2026-07-14T17:12:00Z] Wrote `docs/plan-2026-07-14.md` with hypotheses H2–H7 (score-dominance by license/resolution, regex-fragile license classifier, no dedup, `--fixtures` CLI emits zeros, provenance never gets a real git SHA, Commons yield ceiling is honest hundreds-not-thousands). Seeded `docs/artifacts/` with five paper summaries (RecipeGen CC-BY-NC = reference-only; DenseStep2M training-free step annotation; RECIPE-RL verifier-cheaper-than-labeler; Panda-70M six desirability filters; WBench/WorldPrediction eval dimensions), each with concrete module-level hooks. Added five adversarial test files (license classifier truth-table, provenance+media-url gating, harness determinism, id-dedup xfail probe, CLI-fixtures smoke with strict xfail codifying H5), a `SPECINT-ADVERSARIAL:` pre-commit scanner (`scripts/check_adversarial_todos.py`), and a CI step asserting all four source slugs stay registered. 78 pass, 2 xfailed by design; baseline JSON untouched.

<!-- new entries above this line -->
