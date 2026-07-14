# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-07-14T17:15:30Z] Shipped scorer v2 (procedural verbs + English signal), multi-query `run_matrix` harness, cross-source union-find dedup, page-license lift for Common Crawl (`<link rel=license>` + `<meta>`), and `python -m specint diff` for report-to-report regression checks. v2 beats v1 on `__total__` mean_quality (0.499 → 0.513) without losing license-cleanliness; per-source verdicts logged in `reports/diff-2026-06-20-vs-2026-07-14.json`. CI now enforces strict mypy on core, 85% coverage floor, ruff-format-required, and a diff-based regression gate.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
