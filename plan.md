# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-07-18T17:01:31Z] Filed plan-2026-07-18 attacking the seed baseline on three axes (cross-source dedup, procedural-density scoring, categorymembers discovery), added research notes on WorldPrediction/WorldRoamBench/HowTo100M/Ego4D, and shipped the corresponding code + tests: `specint.dedup`, procedural_density quality component, Wikimedia `category=` mode, license-invariant/baseline-regression tests, CI baseline-regen job, and codespell pre-commit hook. New baseline reports/baseline-2026-07-18.json: wikimedia 0.52 > peertube 0.48 > common_crawl 0.47 > archive_org 0.30 (ranking preserved from 2026-06-20; procedural_density penalizes metadata-sparse fixtures).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
