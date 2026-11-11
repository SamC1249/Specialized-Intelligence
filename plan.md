# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Adversarial-Agent @ 2026-11-11T17:10:02Z] Published `docs/plan-2026-11-11.md` attacking the 2026-06-20 baseline (tiny-N, no cross-source dedup, no license-laundering defense, no procedural signal) with 5 hypotheses + prioritized P0–P3 deliverables; added 5 research-paper artifacts under `docs/artifacts/` (Common Pile v0.1, Web Data Commons Recipe/VideoObject, procedural segmentation SotA, tiered video dedup, egocentric-dataset license landscape).
- [Adversarial-Agent @ 2026-11-11T17:10:02Z] Shipped P0 test/CI hardening to cover the plan: `tests/test_schema_contract.py` (bidirectional `db_structured.md` ↔ Pydantic parity), `tests/test_license_floor.py` (fixture corpus exercises both redistributable and UNKNOWN), `tests/test_baseline_regression.py` (±0.02 drift gate on `reports/baseline-*.json`); pre-commit now runs `codespell` + offline pytest on commit and a coverage-gated full run on push (currently 83%); CI gained matching schema/license/baseline jobs. All 28 tests pass offline.
- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

<!-- new entries above this line -->
