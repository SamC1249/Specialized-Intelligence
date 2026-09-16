# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-09-16T17:30:00Z] Wrote `docs/plan-2026-09-16.md` + five paper-note artifacts (HowTo100M/HT-Step, Ego4D/Goal-Step, Panda-70M, V-JEPA(2), VSC2022/SSCD); attacked six bootstrap weaknesses (CLI `--fixtures` was a placebo, Wikimedia licence heuristic misses `Attribution-ShareAlike`, provenance never captured a real git SHA, no dedup, quality scorer over-weights licence, mypy ran as `|| true`); shipped fixes/tests for `--fixtures`, provenance git SHA, L1+L2 dedup primitives (`quality/dedup.py`), plus `test_license_classification.py` / `test_reproducibility.py` / `test_schema_roundtrip.py` / `test_dedup.py`; added `dependabot.yml`, strict mypy on the schema/quality core, coverage floor 80% (currently 86%), and a `pip-audit` supply-chain CI job. Left four adversarial licence cases as `xfail` for the next Coding-Agent turn.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
