# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-11T17:35:00Z] Shipped multilingual seed terms (11 langs), a metadata-only language-confidence signal, a conservative cross-source dedup (title-bigram + 30s duration bucket), and a weight-vector ablation harness (`python -m specint ablate`) with 4 baseline presets. Fixture upgrade adds a Wikimedia↔archive.org near-duplicate (dedup fires: `cross_source_duplicates=1`, `n_records=11 -> n_after_dedup=10`) plus Spanish/Japanese Commons entries. `reports/compare-2026-08-11.json` mean-quality 0.549 (vs 0.499 seed) and `reports/ablate-2026-08-11.json` picks `license_heavy` (0.574) over `baseline` (0.530) on the current fixtures — useful signal, but the fixture set is still tiny; do not tune WEIGHTS from this alone.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
