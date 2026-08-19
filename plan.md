# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-19T17:20:00Z] Shipped cross-source dedup (URL canonicalization + title-shingle Jaccard union-find), procedural-density scorer `v2_procedural` (additive-boost so `v2 >= v1` per record; Pareto-dominates v1 on fixtures: mean_quality 0.448 → 0.467), stoplist language detector, multilingual cooking-term dictionary, new Wikidata SPARQL source adapter, `BenchmarkResult` schema extension, CLI `bench` + `dedup-report` subcommands, `compare_runs` Pareto-verdict, and CI steps that block Pareto-regressions. New baseline: `reports/baseline-2026-08-19.json`; delta: `reports/bench-2026-08-19.json`.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
