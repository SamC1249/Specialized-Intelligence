# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-08-20T17:01:00Z] Wrote `docs/plan-2026-08-20.md` attacking three weak spots in the seed (no Europeana source, no dedup, no language signal); added `docs/artifacts/{densestep2m,cosmos-curator,mlt-dedup}.md` research notes; shipped Europeana adapter, `quality/lang.py` heuristic detector, `dedup/minhash.py` metadata dedup, adversarial license-classifier tests that surfaced 3 real Wikimedia bugs (Attribution-ShareAlike, Attribution 4.0, PDM 1.0 all classified as UNKNOWN — now fixed); tightened CI with 80% coverage floor and strict-mypy on core modules; refreshed baseline `reports/compare-2026-08-20.json` (11 records, 8 license-clean vs. seed 8/6). 69 tests, all offline.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
