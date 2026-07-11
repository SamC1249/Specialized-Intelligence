# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-07-11T17:15:00Z] Shipped 2026-07-11 adversarial plan + 3 research artifacts (legal corpora, cross-source dedup, world-model quality filters); implemented `dedup.py` (title-trigram Jaccard + duration bucket + author), `domains.py` (cooking/surgery/lab/sports/manufacturing), domain-aware `action_density` quality component with trailer/montage blocklist, real-git-SHA provenance stamping, adversarial NC/ND license fixtures for wikimedia and archive_org (parametric regressions locked in), hypothesis property tests for the Common Crawl JSON-LD parser, and CI hardening (mypy no longer `|| true`, strict mypy on `records.py`, pre-commit adds check-json/check-toml/debug-statements/mixed-line-ending). New fixture baseline `reports/compare-2026-07-11.json` reranks wikimedia 0.52 > peertube 0.49 > common_crawl 0.44 > archive_org 0.32 under the reweighted 6-component scorer; cross-source dedup metrics land in every BenchmarkResult (schema updated in `db_structured.md`).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
