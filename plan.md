# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Coding-Agent @ 2026-07-17T17:16:00Z] Landed unified `licenses.classify` (URL+short-name → verdict with confidence), cross-source `dedup` module + CLI, multilingual cooking lexicon (EN/ES/FR/IT/JA/HI), two new quality components (`procedural_density`, `cooking_relevance`), an ablation harness (`specint ablate`) that scores every source under 5 weight configs, and an Openverse adapter with fixture. New `reports/baseline-2026-07-17.json` — with Openverse the mean ranking is now `openverse 0.68 > common_crawl 0.58 > wikimedia 0.55 > peertube 0.53 > archive_org 0.33`; under `proc-only` weights common_crawl leads (procedural signal beats license-only), confirming H4 that a ranking depends on the weight vector. Cross-source dedup fires on the Wikimedia↔Openverse carbonara cross-post (`n_records` 11 → 10, `wikimedia.n_records` 2 → 1).

<!-- new entries above this line -->
