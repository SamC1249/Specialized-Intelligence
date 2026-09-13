# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-09-13T17:10:00Z] Filed `docs/plan-2026-09-13.md` (H1–H6 attacks: scalar-quality lossiness, URL-only dedup fiction, Common-Crawl parser brittleness, cooking-only scope, prose-only invariants, no regression gate) + 5 artefacts (SolarWM tiered filtering, V-JEPA 2 / VideoMix22M, Panda-70M splitting+desirability, DataComp CommonPool legal template, three-layer dedup contract). Deliverables ordered P0 legality→invariant property tests, P1 metadata-only cross-source dedup + fixture pair, P2 QualityTier + procedural-density, P3 multi-domain `SourceQuery`, P4 regression-gated CI, P5 Common Crawl fixture menagerie.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
