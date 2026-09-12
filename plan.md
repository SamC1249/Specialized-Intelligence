# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-12T17:35:00Z] Added `youtube_cc` metadata-only adapter (URL+metadata, `media_url` always None), scorer `v2` (`procedural_density` + `language_signal`) registered in `SCORERS`, cross-source `dedup` module with normalised-URL/title keys, multilingual `queries` presets, integration-test scaffold, and v1/v2/v2-dedup reports for 2026-09-12. Honest note in `reports/scorer-comparison-2026-09-12.md`: v2 does not beat v1 on aggregate mean quality on fixtures but wins the procedural-vs-lecture discrimination axis (unit-tested); v1 stays default.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
