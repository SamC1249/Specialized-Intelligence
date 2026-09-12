# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-09-12T17:21:31Z] Attacked the 2026-06-20 baseline with `docs/plan-2026-09-12.md` (dedup, cross-source license invariants, yield gap, HowTo100M ASR trap, V3C metadata as next legal source) and 6 research artifacts in `docs/artifacts/`. Shipped Phase-1 near-dup detector (`quality/dedup.py`) + I1–I6 invariants (`quality/invariants.py`) + `specint dedup` / `check-invariants` CLIs + coverage-gated CI (88%) + actionlint & file-length pre-commit hooks; new baseline `reports/dedup-2026-09-12.json` shows 2/12 records collapse (URL dup in wikimedia, title+duration in archive_org).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
