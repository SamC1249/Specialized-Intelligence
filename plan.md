# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-14T17:30:00Z] Centralized license classification (`specint.licenses`), added script/stopword language detector (`specint.language`) + `language_tagged` quality component, added multilingual domain profiles (`specint.domains`, `--domain/--language` CLI + `domains` subcommand), Common Crawl now trusts page-level `<link rel=license>` over lying JSON-LD (new `_lying.html` fixture proves it downgrades to RESTRICTED), fixed `--fixtures` mode to actually load fixture files, and shipped `compare-diff` CLI. New `reports/compare-2026-09-14.json` beats the seed baseline on aggregate mean_quality (0.499 → 0.549, +9.9%) and license-clean count (6 → 7); `reports/diff-2026-09-14.json` records per-source deltas. 63 offline tests green; e2e regression asserts we never drop below the seed baseline again.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
