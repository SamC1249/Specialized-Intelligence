# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-09-15T17:03:00Z] Framed the merge-queue bottleneck (43+ unmerged draft PRs), shipped a linearized 6-step merge order + hypotheses H7–H10 (JSON-LD fuzz, cross-source dedup, Microdata gap, seconds-per-step density), five research artefacts (WorldRover, InternVid, Panda-70M, Wikibooks Cookbook, CC columnar index), and adversarial guardrails (`test_json_ld_robustness`, `test_json_serialization`, `check_plan_entry` pre-commit hook, nightly baseline workflow).

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
