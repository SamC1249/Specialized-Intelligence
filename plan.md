# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-07-11T17:12:00Z] Shipped adversarial plan for 2026-07-11 and implemented: quality scorer v2 (neutral-unknown metadata, license tier, procedural-verb density, resolution×fps combo), cross-source dedup pipeline (url/media/fuzzy-title), multilingual `SourceQuery.languages` + `expand_terms` (12 languages), YouTube CC-only adapter (metadata only, never emits media_url), yield estimator + `python -m specint yield`, head-to-head scorer CLI, integration test scaffold under `pytest -m integration`, and CI matrix extended to 3.13 with coverage artifact and manual-dispatch integration job. New reports: `reports/compare-scorers-2026-07-11.json` (v2 re-ranks archive_org up 0.36→0.45 vs v1) and `reports/yield-2026-07-11.json` (Wikimedia projects ~215 redistributable hours, YouTube 0 redistributable by design). Test count 18 → 62.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
