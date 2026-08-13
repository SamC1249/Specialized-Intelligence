# Web Data Commons — Schema.org Class-Specific Subsets (VideoObject / Recipe)

- Landing page: <http://webdatacommons.org/structureddata/schemaorg/>
- 2024-12 release: extraction over the October 2024 Common Crawl.
- Read on: 2026-08-13 (by `Adversarial-Agent`).

## One-paragraph summary

The Web Data Commons project (Univ. Mannheim) extracts every JSON-LD /
Microdata / RDFa / Microformats block from the Common Crawl corpus and
publishes class-specific subsets (Product, Recipe, VideoObject, Movie,
LocalBusiness, …) as N-Quads. The extractor tool is Apache-2.0. The
resulting data is offered publicly. Per-record licensing is inherited from
the *source page* (fourth column of the N-Quad), which is exactly the model
we already committed to in `AGENTS.md` and `db_structured.md`.

## Why we care

We currently ship `common_crawl.py` as *HTML → schema.org* parser only.
Two problems:

1. Running our own WARC pass is expensive and does not respect the
   comparison-first rule in `AGENTS.md` (no baseline exists for it yet).
2. WDC has already done the extraction; ingesting their dumps is orders of
   magnitude cheaper and more reproducible.

The `Movie` subset alone in 2023-12 was **162 M quads / 2 M URLs / 7 641
hosts**. The `VideoObject` subset is smaller but strictly relevant. All
downloads are N-Quads; we can convert with the WDC-provided helpers, or by
streaming with a stock RDF parser.

## Ideas to implement (queued for a follow-up PR)

- Add a `sources/wdc_videoobject.py` adapter whose `parse()` takes a
  streaming iterator of `(subject, predicate, object, context)` quads and
  emits `VideoRecord` per subject. The `context` field is the source page
  URL — that goes straight into `VideoRecord.url` and (crucially) into the
  license lookup.
- `search()` in this adapter is *not* live network: it takes a local
  N-Quads file path or an HTTPS URL that yields N-Quads. Tests should feed
  a tiny hand-crafted `.nq` fixture.
- License resolution for WDC records should reuse the improved
  `common_crawl` license inference (JSON-LD `license` + `<link rel="license">`
  proven by page HTML if we chose to re-fetch, else `UNKNOWN`).

## Yield estimate (back-of-envelope)

If cooking-relevant hosts are ~1 % of the `VideoObject` universe (recipes
are one of the top-8 uses of `VideoObject` per Google's structured-data
report) and average declared duration is 4 minutes, a single WDC yearly
release should surface ~10⁵ candidate cooking videos before any dedup.
Even at a 90 % dedup rate that's an order of magnitude more than the
combined yield of the four current adapters.

## Risks

- **Silent license drift.** A page can lie about its license in JSON-LD.
  Fallback: treat any WDC record without a *page-verified* license as
  `UNKNOWN` (never redistribute media; keep only URL provenance).
- **Schema drift.** `schema.org/VideoObject` is stable but our extractor
  must tolerate legacy `http://schema.org` vs `https://schema.org`
  `@context` values (both are still in the wild).
