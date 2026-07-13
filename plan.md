# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-07-13T17:14:00Z] Shipped 2026-07-13 plan deliverables: added `youtube_cc` CC-BY adapter (offline fixture), cross-source `deduplicate`/`simhash`/`canonical_key` in `specint.quality.dedup`, offline trigram language detector, two new quality components (`language_confidence`, `procedural_density`), an `ablate` CLI + 6-preset ablation harness that is now emitted per CI build, and a refreshed baseline `reports/baseline-2026-07-13.json` (new ranking with all seven components: youtube_cc 0.61 > wikimedia 0.51 ≈ peertube 0.51 > common_crawl 0.48 > archive_org 0.37) plus `reports/ablation-2026-07-13.json` showing `no_license` drops total mean quality from 0.485 to 0.350, confirming license-clean remains the dominant signal.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
