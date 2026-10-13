# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-10-13T17:10:00Z] Shipped all Priority-A items from `docs/plan-2026-10-12.md` plus Priority-B `quality_hours` and `doctor`: `specint._git.short_sha` ends `extractor_git = "dev"` provenance violation; adversarial + malformed fixtures per source (plus a Wikimedia MIME-over-title tightening); new `reports/baseline-2026-10-13.json` + `baseline-latest.json` + tolerance file wired into a CI regression gate; CLI gains `doctor`; mypy promoted to a hard failure (fixed 7 pre-existing errors + a NoneType `.split()` latent bug in common_crawl); CI gains codespell, scoped lychee link-check, and `pip-audit` (weekly scheduled, blocking). Measured on the shared fixture bundle, `quality_hours` now reveals archive_org (0.192 h) leads despite its lowest mean_quality (0.36) — direct evidence for the Adversarial-Agent critique that `mean_quality` alone biases toward short-clip sources.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
