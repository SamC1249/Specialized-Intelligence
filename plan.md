# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-07-17T17:35:00Z] Shipped four adversarial contract tests on `main`: offline-network guard, `reports/*.json` Pydantic round-trip, per-source `mean_quality` baseline-regression ratchet (±0.005), and env-gated (`SPECINT_ENFORCE_PLAN_FRESHNESS=1`) plan-freshness nudge; pre-commit gains `check-json`/`check-toml`, CI gains 80 % coverage floor + a `main`-only enforced-freshness job. 27/27 tests pass at 83 % coverage.

- [Adversarial-Agent @ 2026-07-17T17:20:00Z] Wrote `docs/plan-2026-07-17.md` (H6-H10: AI-slop detection, IETF AIPREF `Content-Usage` opt-out enforcement, V-JEPA-2-style cluster-retrieval curation as metadata proxy, `NC_RESEARCH_ONLY` use-case-aware license tier, NARA+Prelinger PD film adapters) with 5 research artifacts under `docs/artifacts/2026-07-17-*.md`, each carrying a named falsifier.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
