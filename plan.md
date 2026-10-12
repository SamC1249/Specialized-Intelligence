# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-10-12T17:30:00Z] Shipped `docs/plan-2026-10-12.md` and acted on it: new metadata-only `youtube_cc` adapter (per allowlist: `videoLicense=creativeCommon`, no media download, verifies per-video `status.license`), offline function-word language detector (`en/es/fr/de/it/pt`), procedural-density quality component (now 0.20 of the weighted sum), explicit `training_eligible` / `filter_for_training` license-safety filter with dedicated test, `specint diff a.json b.json` CLI + `compare.diff_reports` for byte-reproducible per-source deltas, `--fixtures` CLI now actually loads committed fixtures, new baseline `reports/baseline-2026-10-12.json` + committed `reports/diff-2026-06-20_to_2026-10-12.json`. Delta vs. 2026-06-20 baseline on the same query: `__total__` n_records 8→11 (+3), n_license_clean 6→8 (+2), total_duration 3021s→6740s (+123%), mean_quality 0.499→0.478 (−0.021, caused by the reweighting adding `procedural_density`). 39 tests passing offline; pre-commit clean.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
