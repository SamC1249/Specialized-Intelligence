# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-18T17:15:00Z] Shipped multi-profile quality scoring (`default`, `procedural`, `resolution`) with 4 new metadata-only components (language stopword detector, procedural verb density, recency, aspect-ratio ok), cross-source dedup (`quality/dedup.py`) with dedup-aware `__unique_total__` benchmark row, new `wikimedia_category` source adapter (`generator=categorymembers`) + fixture, `BenchmarkResult.profile` field, CLI `--profile {default,procedural,resolution,all}` and `profiles` subcommand, parametric license-classifier tests across all adapters, 85% coverage floor enforced in CI, and `reports/compare-2026-08-18.json` where every 2026-06-20 baseline number is held or improved (wikimedia 0.622, peertube 0.572, common_crawl 0.531; archive_org held at 0.358).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
