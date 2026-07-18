# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-07-18T17:15:00Z] Shipped H2/H3/H4 from `docs/plan-2026-07-18.md`: cross-source dedupe (2-signal-minimum), offline heuristic language detector, `procedural_density` scoring component, and `youtube_cc` adapter (metadata-only, CC-license-gated). Harness now emits `pareto_frontier`, `dedupe`, and `language_coverage` sections; `python -m specint compare --dedupe --detect-language` reproduces `reports/baseline-2026-07-18.json`. Total mean quality on fixtures: **0.5252 vs 2026-06-20's 0.4991** (+5.2%); Pareto reduces the 5-source set to {archive_org, youtube_cc}; `youtube_cc` leads at mean 0.78. 48 offline tests, ruff+format clean, integration marker collects 0 without opt-in.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
