# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-08-25T17:35:00Z] Shipped 2026-08-25 adversarial plan + 7 research artifact notes (WDC/TIB/FineVideo/OpenVid/MLT-Dedup/CaptainCook4D/VideoAuteur). Landed three CI hardenings that attack real gaps: `specint.provenance.resolve_extractor_git` wired into every adapter (fixes AGENTS.md rule-#2 `"dev"`-SHA violation), a fixture-baseline regression test locked against `reports/baseline-2026-06-20.json` (enforces rule #3), and an autouse pytest guard that blocks live HTTP unless a test is `@pytest.mark.integration` (enforces rule #4). 27/27 tests green; queued W4–W10 for Coding-Agent.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
