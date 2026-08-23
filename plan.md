# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-23T17:20:00Z] Shipped multilingual seeds (`specint.seeds` covering 12 BCP-47 tags), a multilingual cooking-vocabulary quality signal (`quality.vocab`), cross-source metadata dedup (`quality.dedup`, integrated into the harness `__total__` row via new `n_after_dedup` field), a **metadata-only** YouTube CC-BY listing adapter (`sources.youtube_cc`, live path gated by `YOUTUBE_API_KEY`), matching fixtures + 22 new unit/e2e tests, and CLI `--fixtures-dir` / `--no-dedup` flags. New baseline `reports/baseline-2026-08-23.json`: 5 sources, 10 fixture records, `mean_quality` = 0.478 (vs 0.499 on the 4-source June baseline — informative regression because the new `cooking_vocab` component correctly downweights terse Wikimedia filenames). Ranking on 2026-08-23 fixtures: wikimedia 0.54 ≈ youtube_cc 0.53 ≈ common_crawl 0.54 > peertube 0.49 > archive_org 0.37.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
