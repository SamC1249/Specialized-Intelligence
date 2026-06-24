# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-24T17:23:09Z] Shipped license-confidence per adapter (`license_confidence ∈ [0,1]` on `VideoRecord`), `procedural_density` quality component (verbs + step markers + recipe-step count), eval-set contamination guard (`specint.contamination` + YouCook2-shaped fixture + CLI `--blocklist`), and the `compare.ablation` harness with `python -m specint ablate`. New ablation report (`reports/ablation-2026-06-24.json`) shows `license_clean` is the dominant positive contributor (-0.13 on `mean_quality` when zeroed) while `procedural_density` separates procedural from beauty-shot records. Added `scripts/{precommit_forbid_youtube,manifest_lint,pipeline_dry_run}.py`, wired into pre-commit + CI; pipeline dry-run e2e test asserts byte-stable manifests. 39 tests pass (was 18).
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
