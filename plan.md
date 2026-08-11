# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-08-11T17:30:00Z] Wrote `docs/plan-2026-08-11.md` (H2–H7 + priority-ordered deliverables); added `docs/artifacts/` with 3 research notes (EPIC-KITCHENS is CC-BY-NC → off-limits; use Web Data Commons Recipe subset instead of raw WARCs; SepiaSearch 10×'s PeerTube yield); shipped P0 guardrails: `pytest-socket` network guard, `test_schema_drift.py`, `test_baseline_regression.py`, extended pre-commit + CI (27 tests pass).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
