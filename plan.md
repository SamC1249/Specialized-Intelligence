# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-12T17:30:00Z] Shipped `docs/plan-2026-08-12.md` (attacks yield/dedupe/language gaps in seed baseline). Added `YouTubeCCSource` (creativeCommon-only, media_url never populated), `detect_language` heuristic + new `procedural_density` and `language_match` quality components, `specint.dedupe` fingerprint/overlap module, `run_full_report` with optional dedupe, `python -m specint dedupe` subcommand, respx-mocked integration tests for every adapter's `search()`, and a CI regression guard vs `reports/baseline-2026-06-20.json`. New `reports/compare-2026-08-12.json` shows aggregate mean_quality 0.590 vs 0.499 baseline (+18% relative); youtube 0.82 leads, wikimedia 0.61, common_crawl 0.60, peertube 0.57, archive_org 0.43.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
