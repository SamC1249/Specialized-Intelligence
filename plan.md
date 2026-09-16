# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-16T17:20:00Z] Shipped cross-source dedup (`quality.dedup`, keys on media/native/landing URL then title+duration), multilingual cooking-relevance scorer (`quality.relevance`, EN/ES/FR/JA/HI/ZH/AR), named scoring profiles (`quality.profiles`; frozen `baseline` + new `cooking`), `python -m specint compare-to-baseline` regression CLI, canonical fixture loader with new ES/JA fixtures + adversarial Commons↔Common-Crawl dedup fixture, and pre-commit `check_reports_json` hook. New frozen baseline `reports/baseline-2026-09-16.json` (cooking profile + dedup, 12 records after dropping 1 dup, mean_q **0.586** vs seed 0.499 = **+17.4%**); same-profile expansion `reports/baseline-2026-09-16-baseline-profile.json` isolates the +11.6% pure-yield gain from the +5.2% profile/dedup gain. CI now runs `compare-to-baseline` against the new baseline on every PR at tolerance 0.02.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
