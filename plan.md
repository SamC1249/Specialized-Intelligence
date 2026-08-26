# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Coding-Agent @ 2026-08-26T17:15:00Z] Shipped the 2026-08-25 plan's W4/W5/W6/W10 items on `main`: unified `specint.licenses.classify` (36-case adversarial matrix, wikimedia + archive_org now share it), phase-1 metadata dedup (`specint.dedup` + `n_duplicates_removed` in `BenchmarkResult`, harness dedups the `__total__` row by default), metadata-only YouTube CC-BY adapter (fixture-testable, `search()` gated on `YOUTUBE_API_KEY` + `SPECINT_RUN_INTEGRATION=1`), and a `DurationProfile` refactor + `python -m specint ablate-duration` CLI. New `reports/compare-2026-08-26.json` ranks: youtube_cc 0.639 > wikimedia 0.622 > peertube 0.572 > common_crawl 0.531 > archive_org 0.358 (unchanged pre-existing sources match the baseline exactly). Ablation report shows `long_form` currently underperforms `short_form` by 0.005–0.034 mean_quality on our short-fixture corpus — informative negative until we backfill long-horizon fixtures.

<!-- new entries above this line -->
