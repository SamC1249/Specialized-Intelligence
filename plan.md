# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-08-25T17:45:00Z] Shipped 2026-08-24 plan P0/P1/P2/P3: `compliance/rights` (robots/TDMRep/ai.txt parsers + fixtures + fail-closed `is_permitted`), `Provenance.raw_sha256` + real git short SHA via `gitmeta`, `dedupe/urlhash` (canonical URL + shingle Jaccard) with `__deduped__` harness row, two new legal sources (`youtube_cc` metadata-only w/ contradiction guard, `peertube_federation` w/ actor-id dedup), procedural signals (`aspect_ratio`, `audio_present`, `cooking_verbs`, `shot_density`) registered under `WEIGHTS_EXPERIMENTAL` with paired A/B report — informative negative: baseline wins on today's fixtures (Δmean_quality = −0.030 on `__deduped__`), so weights are *not* promoted; new baseline in `reports/baseline-2026-08-25.json`, regression gate blocks any per-source drop > 0.05, CI adds abtest step + nightly Python 3.13 job.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
