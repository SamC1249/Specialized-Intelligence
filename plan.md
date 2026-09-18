# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Adversarial-Agent @ 2026-09-18T17:35:00Z] Wrote `docs/plan-2026-09-18.md` attacking H2 (PeerTube under-fanout, uncounted cross-source overlap, unvalidated scorer weights, missing YouTube-Commons ingest); seeded `docs/artifacts/` with three research notes (frontier video-model landscape incl. V-JEPA 2/2.1 mixture reweighting, Sekai2, YouTube-Commons, WDC + CC URL Index, Commons Impact Metrics, PhaKIR/LEMON surgery license desert; dedup primer; 12 adversarial findings).
- [Adversarial-Agent @ 2026-09-18T17:35:00Z] Shipped hardening in this PR: benchmark regression guard (`tests/test_benchmark_regression.py` locks per-source `mean_quality` and `n_records` vs `reports/baseline-2026-06-20.json`), schema drift guard (`tests/test_schema_docs_sync.py` enforces `db_structured.md` ↔ Pydantic model parity), pre-commit hooks (codespell, check-json, mixed-line-ending), and a nightly `pip-audit` GitHub Action. Pre-commit + `pytest` (29 tests) green.

<!-- new entries above this line -->
