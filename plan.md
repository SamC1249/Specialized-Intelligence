# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-08-18T17:12:18Z] Wrote `docs/plan-2026-08-18.md` attacking the 2026-06-20 baseline (fixture-only N=8, schema-availability quality bias, unenforced provenance SHA, no dedup, no gold set); shipped `docs/artifacts/2026-08-18-{datasets,yield-model}.md` cataloguing legally-clean cooking corpora (CaptainCook4D Apache-2.0, COM Kitchens MIT, Web Data Commons dumps) and rejecting Ego4D + EPIC-KITCHENS; hardened CI (coverage floor 80% overall + 95% on the pure core, 800-line file cap, no-live-URL-in-tests guard, pre-commit inlined, nightly integration workflow) and pre-commit (mypy hook, custom guards); added `compare/dedupe.py` + env-driven `Provenance.extractor_git`; and landed 5 adversarial tests (dedupe, cross-domain retargeting, integration-marker enforcement, provenance-SHA, xfail-tracked H3 quality-scorer bias).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
