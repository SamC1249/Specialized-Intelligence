# Web Data Commons — pre-extracted schema.org from Common Crawl

*<http://webdatacommons.org/structureddata/>*

## What it does

- Every Common Crawl release, WDC re-runs the Any23 parser over the
  full corpus and publishes **class-specific N-Quad subsets** for
  every schema.org type: `Recipe`, `HowTo`, `VideoObject`, `Article`,
  ....
- October-2024 corpus (released 2025-01-10):
  - `overall` ≈ **16.5M PLD (pay-level-domain) partitions, 74B
    quads**.
  - `html-mf-hrecipe` (microformat recipes): ~627K URLs, 2.75B
    quads.
  - `schema.org/VideoObject` is in the 1M–10M-domains bucket per
    Google's July 2026 aggregate.
- Data is CC-BY the extractor, and each triple carries the source
  URL — provenance-friendly out of the box.

## Why it matters for us

- Our current `common_crawl` adapter parses individual HTML pages
  one at a time. That is `O(pages_we_have_downloaded)`, which is
  ~0 without an actual crawl. WDC hands us the answer for the
  entire crawl, filtered to only pages that even *declare* a video
  or recipe, at zero crawl cost and inside our legal envelope.
- Turning our `common_crawl` adapter into a **WDC N-Quad
  consumer** first (with our current HTML parser kept as a
  fallback for hot pages) is the single largest yield-per-hour
  lever visible today.
- Because WDC ships class-specific subsets, we can also stand up a
  cheap `HowTo` adapter that captures step-text without needing a
  `Recipe` outer wrapper — this maps to non-cooking procedural
  domains (surgery how-to, lab-protocol how-to) with no code
  change.

## How we'd use it here

- **Plan hook:** H5 in `docs/plan-2026-09-14.md`; concrete
  deliverable: `CommonCrawlRecipeSource.from_wdc_nquads(path)`.
- **Fixture strategy:** ship a hand-authored ~40KB `.nq` with 3
  synthetic recipes so unit tests stay fast and the real WDC
  shard stays out of git.
- **Legal check:** WDC is CC-BY; we must attribute in our
  provenance chain. Add `WDC (Common Crawl)` to `Provenance.
  extractor` when this codepath is used.
- **Benchmark row:** the compare harness gets a new `common_crawl_wdc`
  slug so we can measure yield delta vs the HTML-page path directly.

## Citation

Bizer et al., *Web Data Commons Extraction Report — October 2024
Corpus*. <https://webdatacommons.org/structureddata/2024-12/stats/stats.html>
