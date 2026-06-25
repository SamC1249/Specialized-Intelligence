# AGENTS.md

Operating contract for AI agents collaborating on **Specialized-Intelligence**.

## Mission

Find, evaluate, and harvest **internet-scale, legally accessible** data for
frontier model training. The current narrow target is **cooking / food videos
for world-model training**, but every system must generalize to other
"difficult video" domains (surgery, lab work, sports, manufacturing, etc.).

Hard constraints:

1. **No paid datasets, no paywall scraping, no ToS violations.** Only
   permissively-licensed (CC-BY, CC0, public domain), explicitly-allowed
   public APIs, or fair-use derivatives (frames + URL provenance, not bulk
   redistribution of copyrighted media).
2. **Provenance is mandatory.** Every record must carry source URL, license,
   capture timestamp, and the exact extractor commit hash.
3. **Comparable, not anecdotal.** New sources, scrapers, or quality filters
   must come with a benchmark entry in `src/specint/compare/` so improvements
   are measured, not asserted.
4. **Reproducible offline tests.** CI must pass without network. Use fixtures
   in `tests/fixtures/`, never live HTTP in unit tests.

## Roles

| Identity              | Responsibility                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `Adversarial-Agent`   | Writes the daily plan in `docs/plan-YYYY-MM-DD.md` proposing experiments, attacks on weak spots, and explicit hypotheses to test. |
| `Coding-Agent`        | Implements the highest-leverage items from the most recent adversarial plan, ships tests + CI, and appends a 1–2 line summary to `plan.md`. |
| `Reviewer-Agent`      | (future) Audits PRs for license compliance, test coverage, and reproducibility. |

## Daily Loop

1. Read **all** files in `docs/plan-*.md`, sorted by date; act on the most
   recent unresolved items. If multiple plans exist, prefer the latest but
   carry forward unfinished items.
2. Branch off `main` (Cloud Agents already do this).
3. Implement → add tests → run `pytest` and `pre-commit run --all-files`
   locally before pushing.
4. Append one entry to `plan.md` of the form:
   `- [Coding-Agent @ YYYY-MM-DDTHH:MM:SSZ] one or two lines about what shipped or was ideated.`
5. Open a PR; do **not** self-merge.

## Code Layout

```
src/specint/
  sources/   # one adapter per upstream data source, all subclass BaseSource
  quality/   # heuristics that score a VideoRecord
  compare/   # benchmark harness; emits JSON reports under reports/
  cli.py     # `python -m specint <command>`
tests/       # pytest, offline only (use fixtures)
docs/        # plans + research notes
```

Per repo style rules: keep individual files under ~800 lines, prefer pure
functions, type-annotate public APIs, avoid narrating-the-code comments.

## Comparison-First Rule

Any new collection method or filter must:

- emit a `BenchmarkResult` row (see `src/specint/compare/harness.py`),
- be runnable via `python -m specint compare --source <name>`,
- and the resulting JSON must be committed under `reports/`.

If you cannot beat the current baseline on a defensible metric, document
**why the experiment was still informative** in your plan summary.

## Legal Source Allowlist (current)

- Wikimedia Commons (CC-BY-SA, CC0, PD)
- Internet Archive (per-item license, filtered)
- PeerTube federated instances (per-instance + per-video license)
- Common Crawl (only public-license recipe pages with `VideoObject`
  schema.org metadata)
- YouTube Data API **only** for `videoLicense=creativeCommon` listings
  (URL + metadata, no media download)

Anything else requires an entry in the next adversarial plan justifying
inclusion.
