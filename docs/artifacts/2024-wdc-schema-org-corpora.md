# Web Data Commons — schema.org corpora over Common Crawl (2024/2025 release)

- **Source.** Web Data Commons (WDC) — RDFa/Microdata/Microformats +
  Embedded JSON-LD extractions from Common Crawl. Latest release: Oct 2024
  crawl, published 2025-01-10.
  <http://webdatacommons.org/structureddata/>
- **License.** Published for research purposes; underlying Common Crawl is
  released for permissive use, but *per-page* copyright of the crawled
  content is unchanged and must be respected.
- **Claim we care about.** WDC already extracts class-specific subsets
  (incl. `Recipe`, `VideoObject`) from the entire monthly CC. That means we
  can bootstrap our Common Crawl adapter *without* re-doing the 4,600
  machine-hour parse ourselves — the N-Quad and JSON table dumps are
  directly downloadable.

## Method summary

- WDC runs Any23 against every WARC in a monthly Common Crawl, emits
  N-Quads with page provenance, and groups by schema.org class.
- The 2023 release added a **Schema.org Table Corpus**: 5M pandas-readable
  JSON tables, one per (class, host).
- Growth of `Recipe` and `VideoObject` classes is consistent year over
  year; WDC publishes per-class deployment stats we can use as a *ceiling*
  estimate for our yield budget.

## What it changes for us

1. **Replace our synthetic Common Crawl fixture with a real WDC row** for
   `Recipe` (and later `VideoObject`) in `tests/fixtures/common_crawl/`.
   Keep the current fixture as a "hand-crafted minimal" case; add a second
   fixture drawn verbatim from a WDC N-Quad snippet.
2. **Bulk-yield estimator.** Add a `python -m specint estimate` (future)
   that reads WDC's per-class page counts and multiplies by our empirical
   video-page hit rate (currently ≈ 1 / *n*). No implementation today —
   scope in the plan.
3. **Page-license, not video-license.** Reconfirms our AGENTS.md rule:
   for CC-sourced pages, the *page* license (or `dct:license`) is what
   matters. Add a unit test that ensures our Common Crawl adapter never
   inherits a permissive license from an embedded video's schema without
   also seeing a page-level license.

## Risks / disagreements

- WDC's "class-specific subset" merges JSON-LD + Microdata; the same page
  can appear twice, so any yield estimate has to dedupe by `page_url`
  before counting.
- Any23 is Java-heavy. We keep our extractor in Python (already do) but
  test it against WDC dumps to stay comparable.
