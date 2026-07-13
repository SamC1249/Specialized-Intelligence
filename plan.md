# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-07-13T17:11:10Z] Shipped `docs/plan-2026-07-13.md` (hypotheses H2–H5), 4 research notes in `docs/artifacts/` (V-JEPA 2, Action100M, WDC schema.org, perceptual video hashing), metadata-only `quality/dedup.py` with harness `--dedupe` flag, fail-closed `scripts/policy_lint.py` + pre-commit + CI job (license/host allowlists), CI coverage floor `--cov-fail-under=80`, env-gated `nightly-integration.yml`, real fixture-loading in `--fixtures` mode, and new baselines `reports/baseline{,-dedupe}-2026-07-13.json`. H3 falsified on current fixtures (0 collapses) — flagged as adversarial fixture-set gap for Coding-Agent.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
