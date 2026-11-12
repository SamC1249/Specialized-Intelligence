# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-11-12T17:30:00Z] Shipped `docs/plan-2026-11-12.md` (hypotheses H2–H12 attacking baseline, 10 defects inventoried) + 5 research notes under `docs/artifacts/` (Cosmos-WFM, HD-EPIC/Ego2World, CaptainCook4D, VidaForge, pHash/TransNetV2) + cross-adapter license invariant test + baseline-regression gate script with its own tests + registry-consistency pre-commit hook wired into CI.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
