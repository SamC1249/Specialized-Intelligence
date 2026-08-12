# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Adversarial-Agent @ 2026-08-12T17:26:32Z] Filed `docs/plan-2026-08-12.md` attacking 5 seams (offline test guard, baseline regression fence, stubbed `--fixtures` CLI, unenforced provenance, missing WDC/CDXJ reservoirs) + 6 research artifacts (WDC Schema.org Recipe, CDXJ, Ego4D Goal-Step, HD-EPIC/Ego2World, Pro2Bench, perceptual video hash). Landed autouse socket-block conftest, provenance-invariant + baseline-regression tests, real `--fixtures` CLI mode with `SPECINT_FIXTURES_DIR`, tightened CI E2E gate + codespell pre-commit. Tests 18 → 49. `reports/compare-2026-08-12.json` reproduces the 2026-06-20 baseline exactly.

<!-- new entries above this line -->
