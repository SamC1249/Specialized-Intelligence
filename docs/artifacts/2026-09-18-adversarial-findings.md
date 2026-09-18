# Adversarial findings against the current pipeline — 2026-09-18

`Adversarial-Agent` review of the code that shipped on 2026-06-20. Every
finding here has a proposed test that a Coding-Agent can add. Findings
marked (**shipped**) already have a regression guard landed in this PR;
the rest are enumerated as concrete deliverables in
`docs/plan-2026-09-18.md`.

## A. Yield / coverage attacks

**A1. PeerTube fanout is 3 of ~2 095 instances.**

- Evidence: `src/specint/sources/peertube.py::DEFAULT_INSTANCES` lists 3
  hosts (`framatube.org`, `video.blender.org`, `tilvids.com`). Fediverse
  stats snapshot 2026-05-09 reports **2 095 active instances,
  1 680 711 videos**.
- Attack: our reported PeerTube yield is a floor bounded by three
  admin-curated instances; the *true* CC-BY yield is ≥ 2 orders of
  magnitude higher.
- Fix: use SepiaSearch federated endpoint
  (`https://sepiasearch.org/api/v1/search/videos`) as the primary
  transport; keep per-instance as fallback.
- Proposed test: fixture `peertube/sepia_search.json` with cross-instance
  results; assert `len({r.provenance.query for r in parsed}) == 1` (one
  federated call) and `len({host_of(r.url) for r in parsed}) >= 3`.

**A2. YouTube-Commons is not ingested.**

- Evidence: `AGENTS.md` allowlist permits YouTube for
  `videoLicense=creativeCommon`. PleIAs YouTube-Commons is a 2M-row
  Parquet of exactly that slice. We ingest zero rows.
- Fix: `sources/youtube_commons.py` that consumes a local Parquet path
  (offline for tests; live download optional).
- Proposed test: fixture of 5 rows in Parquet or JSON-line form; assert
  license classification is `CC_BY` and provenance carries the row hash.

**A3. Common Crawl adapter has no `search`.**

- Evidence: `common_crawl.py::search` returns `[]`. That means the CLI
  cannot run this adapter live under `SPECINT_RUN_INTEGRATION=1`.
- Fix: query the URL Index via DuckDB against S3 (Parquet HTTP is
  Range-friendly), keep the parse path unchanged. Alternatively consume
  a WDC subset. Either way, ship one live-integration test guarded by
  the env flag.

## B. Quality-score attacks

**B1. Weights are unvalidated.**

- Evidence: `quality/metrics.py::WEIGHTS = {license:0.35, duration:0.15,
  resolution:0.20, text_density:0.15, has_steps:0.15}`. There is no
  external signal used to justify them; the baseline report simply
  compares aggregates against those weights.
- Fix: `quality/validate.py` computes Spearman ρ between the current
  score and (a) log(1 + Commons Impact Metrics plays) for Commons rows
  and (b) FineVideo `quality_grade`-like metadata where available.
  Report ρ per source in the benchmark row (new field
  `external_correlation`).

**B2. Cooking-only fixtures don't test generalisation.**

- Evidence: `tests/fixtures/{wikimedia,archive_org,peertube,common_crawl}`
  all use cooking/recipe terms. The mission is video *world modelling*
  generally; the current tests cannot detect a scorer that overfits
  cooking vocabulary.
- Fix: add fixtures for at least two non-cooking domains
  (e.g. `subject:science` on IA, `Category:Videos of surgery` on
  Commons). Add an e2e test that asserts mean quality changes < 15 %
  across domains — heuristics should not be domain-specific.

**B3. Long-single-take runtime is ignored.**

- Evidence: `_score_duration` peaks at 300 s (5 min) and decays after. But
  P-JEPA (2026) explicitly benefits from 30-min single-takes; V-JEPA
  2.1 up-weights long web video 3.8×.
- Fix: add a `single_take_bonus` component that rewards
  `duration_s ≥ 600` linearly to a plateau at 1800 s. Re-run the
  baseline; document any inversions.

## C. Provenance / license attacks

**C1. `extractor_git` is always `"dev"` in-process.**

- Evidence: `records.py::Provenance.extractor_git = "dev"` default is
  never overridden; nothing in the codebase calls `git rev-parse` or
  reads `SPECINT_GIT_SHA`.
- Fix: helper `specint.provenance.git_sha()` that (a) reads
  `SPECINT_GIT_SHA` env var, (b) falls back to `git rev-parse
  --short HEAD` via subprocess in a try/except, (c) defaults to `"dev"`.
  Bake into `Provenance.__init__` via a factory.

**C2. License string-match is brittle.**

- Evidence: `wikimedia._coerce_license` upper-cases and looks for
  `"BY-SA"`, `"CC0"`, etc. But Commons uses `{{PD-USGov}}`,
  `{{Attribution}}`, and many other templates whose short name is
  ambiguous. `UsageTerms` and `Copyrighted` extmetadata fields carry
  authoritative signals we currently ignore.
- Fix: enrich `_coerce_license` to consult (a) `LicenseShortName`,
  (b) `UsageTerms`, (c) `Copyrighted`. If any two disagree, downgrade to
  `License.UNKNOWN` and emit a `LicenseConflictError` in the extractor
  provenance.

**C3. No dedup across sources.**

- Evidence: `compare/harness.py::run_comparison` sums per-source rows
  into `__total__` without checking for cross-source duplicates. A CC
  Commons file mirrored on Framatube and Archive.org contributes 3x.
- Fix: canonical-URL + duration-bucket dedup (see
  `docs/artifacts/2026-09-18-deduplication-primer.md`). Add
  `n_duplicates_removed` to `BenchmarkResult`.

## D. CI / infra attacks (**shipped in this PR**)

**D1. No benchmark-regression guard** (**shipped**).

- Evidence: nothing fails when `mean_quality` drops. A subtle scorer
  regression could ship green.
- Fix landed in this PR: `tests/test_benchmark_regression.py` runs the
  offline harness across all four fixture sources and asserts that per-
  source `mean_quality` is within `−0.02` of the values recorded in
  `reports/baseline-2026-06-20.json`.

**D2. Schema doc can drift from `records.py`** (**shipped**).

- Evidence: `db_structured.md` is prose; if someone adds a Pydantic field
  and forgets to update the doc (or vice versa), nothing complains.
- Fix landed in this PR: `tests/test_schema_docs_sync.py` parses the
  Markdown tables and asserts every documented `VideoRecord`,
  `Provenance`, `SourceQuery`, and `BenchmarkResult` field appears in
  the corresponding Pydantic model (and vice versa).

**D3. Pre-commit misses common English typos / trailing tabs / dead links**
(**shipped**).

- Fix landed in this PR: add `codespell` and `check-json` /
  `mixed-line-ending` hooks; add a nightly GitHub Action that runs
  `pip-audit` against the frozen requirements.

## E. Legal-classification bug bounty (open)

We should treat *any* record whose license we tag as redistributable but
that turns out not to be as a P1 bug. Add a manual review step:

- `python -m specint audit --output reports/audit-YYYY-MM-DD.json` picks
  N random records per source, prints the license URL and
  `LicenseShortName`, and requires a human sign-off before the record
  set can be marked "training-eligible."
