# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-13T17:45:00Z] Shipped language detection (unicode + stopword, en/es/ja/fr/de/it/pt/zh/hi/ar), procedural_density scoring, cross-source dedupe with (normalised_title, duration_bucket) fingerprints + JSON overlap matrix, weight-ablation harness with baseline/license_heavy/procedural_heavy variants, respx-mocked search() tests, hard mean_quality regression guard (0.45), new CLI subcommands `dedupe`/`ablate` and `compare --dedupe`/`--multilingual`. `reports/compare-2026-08-13.json` lifts __total__ mean_quality from 0.499 → 0.599 on the same fixture universe; ablation ranks license_heavy (0.656) > baseline (0.593) > procedural_heavy (0.511) — future weight PRs must beat both on this benchmark.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
