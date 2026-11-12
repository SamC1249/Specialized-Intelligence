# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-11-12T17:15:00Z] Shipped multilingual language detector + cooking-relevance scorer, quality weight profiles (`v1` reproduces 2026-06-20 baseline exactly, `v2` and `v2_cooking` add relevance), cross-source dedup module, Common Crawl `contentUrl` → `RESTRICTED` mitigation for commercial-host embeds (YouTube/Vimeo/TikTok/etc.), ablation harness + `python -m specint ablate|dedup` CLIs, new fixtures (Spanish Wikimedia, French PeerTube, YouTube-embed recipe page), committed `reports/compare-2026-11-12.json` + `reports/ablate-2026-11-12.json` + `reports/dedup-2026-11-12.json`, CI gained ablate/dedup/JSON-validity steps and pre-commit JSON check. 54 tests pass offline. Ablation finding: v1 ranks wikimedia > peertube > common_crawl > archive_org; v2_cooking flips to common_crawl > peertube > wikimedia > archive_org — baseline weights were under-weighting relevance.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
