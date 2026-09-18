# plan.md — Daily Log

One or two lines per agent per day. Newest entries on top. See
`docs/plan-YYYY-MM-DD.md` for the full daily plans.

- [Coding-Agent @ 2026-09-18T17:20:00Z] Carried forward the seed plan's unresolved items: unified regex-based license classifier (`quality/licenses.py`) shared by wikimedia + archive_org + common_crawl (kills the per-source mis-labeling risk called out as an adversarial risk), page-level `rel="license"` extraction for Common Crawl recipe pages (embedded VideoObject license is no longer trusted blindly), offline BCP-47 language detector + `language_known` quality component + multilingual seed terms (en/es/fr/de/it/pt/nl), first `youtube_cc` adapter (metadata-only, `videoLicense=creativeCommon` filter, live path double-gated by `SPECINT_RUN_INTEGRATION` + `YOUTUBE_API_KEY`), and a `compare-diff` CLI + `compare/diff.py` module + regression-guard test that fails CI if `n_license_clean` or `total_duration_s` drops below the June baseline. Fixture-baseline `reports/baseline-2026-09-18.json`: total license-clean records 6→9 (+50%), total duration 3021s→5422s (+79%), mean_quality 0.499→0.522. Per-source: common_crawl 0.53→0.75 (page-license lift), youtube_cc new at 0.42, archive_org 0.36→0.42 (language detection), wikimedia 0.62→0.56 (upstream doesn't declare BCP-47 language — flagged as next-round adversarial target).

<!-- new entries above this line -->
