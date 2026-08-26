# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-06-20T17:12:32Z] Bootstrapped repo: `AGENTS.md`, canonical `db_structured.md` schemas, four offline source adapters (Wikimedia Commons, Internet Archive, PeerTube, Common Crawl recipe JSON-LD), metadata-only quality scorer, comparison harness + CLI, fixture-driven e2e test, GitHub Actions CI matrix on 3.11/3.12, and pre-commit. First baseline `reports/baseline-2026-06-20.json` ranks sources by mean quality: wikimedia 0.62 > peertube 0.57 > common_crawl 0.53 > archive_org 0.36 — future PRs must beat this on the same fixtures.

- [Adversarial-Agent @ 2026-08-26T17:15:00Z] Posted `docs/plan-2026-08-26.md` attacking H2 (scorer is decorative): added utility-calibration + narration-density + cross-source dedup as concrete deliverables. Landed 3 adversarial CI defenses (`test_adversarial_license_audit.py`, `test_adversarial_provenance.py`, `test_adversarial_schema_regression.py`), added codespell + blocking mypy-on-schema to pre-commit, and split CI mypy into blocking (schema) + best-effort. Recorded 4 research artifacts (V3C, HD-EPIC/Ego2World, Common Crawl URL index, MLT-Dedup/VidDup/forge) under `docs/artifacts/`.

<!-- new entries above this line -->
