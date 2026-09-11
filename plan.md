# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-11T17:30:00Z] Shipped cross-source dedup (`specint.dedup`) + a selectable v2 quality profile that rewards cooking-verb density, extended `BenchmarkResult` with `profile` / `n_unique` / `duplicate_rate` (backward-compat defaults), added a metadata-only yield estimator (`specint.estimate` + `python -m specint estimate`), and wrote `docs/plan-2026-09-11.md` carrying forward H2/H3/H4 from the seed plan. New reports under `reports/compare-2026-09-11*.json` show the intentional NASA fixture dupe now surfaces as duplicate_rate=0.091 across (wikimedia, archive_org); CI gained a v2+dedup lane that asserts this.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
