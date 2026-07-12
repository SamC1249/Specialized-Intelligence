# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-07-12T17:45:00Z] Shipped domain registry (`cooking`/`laboratory`/`surgery`/`sports`/`manufacturing`), Common Crawl page-level CC license extraction (`<link rel="license">` / `dcterms.rights` / body CC anchors), cross-source dedup (`pipeline.dedup_records` with URL + media_url + title-shingle+duration-bucket signals, deterministic survivor), quality scorer v2 (graded `license_tier` + domain-aware `procedural_density`; v1 preserved for ablation), an ablation harness, and CLI `domains`/`ablate` subcommands. New baselines in `reports/compare-2026-07-12-{cooking,laboratory}.json` + `ablation-2026-07-12.json`; e2e proves the laboratory domain runs through the same harness with no code changes (H1). CC-BY / CC-BY-SA fixtures push common_crawl mean quality from 0.53 → 0.59 and `n_license_clean` from 0 → 2 without silently upgrading unlicensed pages.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
