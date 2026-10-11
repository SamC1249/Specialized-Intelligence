# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-10-11T17:22:36Z] Carried forward unresolved items from `docs/plan-2026-06-20.md`: added page-level CC-license detection to the Common Crawl adapter (addresses risk #2 — new baseline promotes 1 extra CC-BY record), introduced cross-source dedupe + new `BenchmarkResult` columns (`license_clean_hours`, `top10_mean_quality`, `median_height`, `n_with_steps`, `n_duplicates_dropped`), replaced the binary `has_steps` quality lever with a graded `procedural_density` component (steps + cooking-verb density + measurement-phrase density), shipped 13-language seed terms + script-based language inference, made `--fixtures` load real sample data via `compare/fixtures.py`, added `specint diff` subcommand wired into CI, and committed `reports/baseline-2026-10-11.json` (__total__ mean_quality 0.499 → 0.522, n_license_clean 6 → 7).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
