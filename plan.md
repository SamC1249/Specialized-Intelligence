# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-08-23T17:20:00Z] Wrote `docs/plan-2026-08-23.md` (H2: opt-out + dedup + transparency Pareto-dominate the 2026-06-20 baseline) + six research artifacts under `docs/artifacts/` (Ego2World, DenseStep2M, MLT-Dedup, streaming-world-model, EU AI Act Art.53(1)(d), TDMRep/AIPREF, SepiaSearch). Shipped test-discipline attacks today: `tests/test_invariants.py` (license/provenance/id-stability/registry parametrised over every source), `tests/test_baseline_regression.py` (locks the 2026-06-20 mean-quality band), `scripts/audit_fixtures.py` + new pre-commit hook, and a `transparency-lint` CI job placeholder. 26 new tests, all offline, all green.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
