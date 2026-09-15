# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-15T17:30:00Z] Shipped cross-source `deduplicate()` + `DedupReport` (media_url / url / title×duration×author fingerprint), procedural-density scorer + named `SCORING_PROFILES` (`balanced`, `license_first`, `procedural_first`), `run_ablation` + `python -m specint ablate|dedup` subcommands, multilingual seed-term catalog (en/es/fr/de/it/pt/ja/zh), YouTube CC-BY listings adapter (metadata-only, `YOUTUBE_API_KEY`-gated), `provenance_git.current_git_sha()` wired into every adapter, and `scripts/emit_baseline_reports.py`. New reports `reports/{compare-balanced,ablation,dedup}-2026-09-15.json` show `youtube_cc` (mean 0.59) top under `balanced` and `common_crawl` (0.59) top under `procedural_first` — `ranking_agreement=false` confirms H4 (source ordering is profile-dependent). CI now runs `compare`/`ablate`/`dedup` + the shipped-fixture baseline script and uploads all six artifacts.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
