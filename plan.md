# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-09-14T17:12:00Z] Wrote `docs/plan-2026-09-14.md` (H2-H6: fixture over-fit, Europeana/LoC/NASA gap, Sepia-Search PeerTube federation, Web Data Commons swap-in, silent provenance-git regression). Shipped guardrail tests (`test_offline_contract.py` socket-sentinel, `test_baseline_nonregression.py` vs `reports/baseline-2026-06-20.json`, `test_provenance_integrity.py` with an xfail pin on the `extractor_git="dev"` bug), a `scripts/check_file_size.py` pre-commit + CI hook, and 5 research/system artifacts under `docs/artifacts/` (ACTION100M, V-JEPA 2, Panda-70M, Web Data Commons, Europeana+LoC+NASA, Sepia Search). CI still green: 29 passed, 1 xfailed.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
