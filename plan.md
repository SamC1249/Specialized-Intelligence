# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-11-11T17:30:00Z] Shipped `QualityProfile` registry (`baseline` frozen + new `v2` adding multilingual cooking relevance EN/ES/FR/DE/IT/JA, procedural density, language-known), cross-source `dedupe` (normalized-title + duration-bucket, license-clean-preferring winner), `YieldEstimate` per-source estimator with upstream-cap awareness, extended `BenchmarkResult` with `profile`/`n_unique_after_dedupe`, new CLI `compare --profile {baseline,v2,all}` + `dedupe` + `yield`, 25 new offline tests (43 total passing) including a regression guard that fails if `baseline` numbers drift from `reports/baseline-2026-06-20.json`, plus `reports/compare-profiles-2026-11-11.json` showing v2 __total__ mean_quality 0.5701 > baseline 0.5347 (+6.6%) and `reports/dedupe-2026-11-11.json` finding 2 cross-source mirror duplicates on the enlarged fixture set.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
