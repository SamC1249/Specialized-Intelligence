# 02 — Common Crawl URL Index for video discovery

**Status:** proposed (Priority-C in `plan-2026-10-12.md`).
**Hypothesis served:** H2 (yield) via Common Crawl at scale.

## Problem

Our current `CommonCrawlRecipeSource` only parses an HTML blob you
hand it. In production that means someone has to pre-select pages,
which is exactly the hard part. Common Crawl itself ships two indexes
that make page selection cheap:

- **CDXJ Index** (legacy): URL-keyed, JSONL per crawl segment.
- **URL Index** (formerly "Columnar Index"): Apache Parquet, stored
  at `s3://commoncrawl/cc-index/table/cc-main/warc/`, partitioned by
  `crawl` (e.g. `CC-MAIN-2026-30` for July 2026) and `subset`. Query
  with AWS Athena, Spark, Pandas, Polars, Arrow, or DuckDB.
  Reference: [Common Crawl URL Index][cc-url-index].

The URL Index exposes `url_host_registered_domain`,
`content_mime_type`, `content_charset`, `warc_filename`,
`warc_record_offset`, `warc_record_length`, so we can:

1. Filter HTML pages on cooking-adjacent domains (via a committed
   annotation table of recipe sites or by regex on hostnames).
2. Pull the targeted WARC byte ranges only, instead of streaming
   full WARCs.
3. Parse those pages with the *existing* `parse_recipe_html` function.
4. Extract `schema.org/VideoObject` with `license` / `sdLicense` /
   `acquireLicensePage` / `usageInfo` fields.
   Reference: [schema.org VideoObject][schema-video-object].

## What LAION-BVD teaches us

LAION-BVD mined **1.3B platform-specific video URLs** out of Common
Crawl, downloaded 80M (10M hours), scene-split them, and captioned.
It is explicitly non-commercial, so we can't ingest it, but their
pipeline design is public: iterate the CC index → extract candidate
URLs → scene-detect → caption. See
[`docs/artifacts/papers/README.md`][papers]. We can replicate the
*URL-discovery* half under our tighter license filter.

## Risks (adversarial)

- **S3 egress cost.** URL Index queries bill the requester once you
  leave Common Crawl's free S3 bucket, and byte-range WARC fetches
  from `https://data.commoncrawl.org/` are free but rate-limited.
  Build the client to only ever hit these two endpoints, never a
  mirror.
- **License-on-page vs. license-of-video.** A page can be CC-BY while
  embedding a YouTube iframe; the embedded video is *not* CC-BY.
  Treat `page.license` as a necessary but not sufficient signal; the
  JSON-LD `VideoObject.license` wins when present.
- **CI must stay offline.** Build the DuckDB-driven path so it reads
  from a small checked-in Parquet fixture (<= 1 MB), not S3. Fail
  loud if the production path is reached without
  `SPECINT_RUN_INTEGRATION=1`.
- **Row count drift.** CC publishes a new crawl every month. Pin to a
  specific `crawl=CC-MAIN-YYYY-WW` in reports so comparisons are
  dated correctly.

## Proposed design

- New module `src/specint/sources/common_crawl_index.py`.
- Pure functions:
  - `select_candidates(parquet_path, domains, limit) -> list[Candidate]`
    using DuckDB over Parquet (works both for the S3 URL Index and
    for a local fixture Parquet).
  - `fetch_warc_range(warc_filename, offset, length, client)` →
    returns gzipped HTML.
  - `parse_warc_html(html, url, query)` reuses
    `common_crawl.parse_recipe_html`.
- Fixture: `tests/fixtures/common_crawl_index/mini.parquet` (<=
  1 MB) with 20 synthetic rows pointing at a local
  `tests/fixtures/common_crawl_index/mini.warc.gz` with 3 real
  recipe HTML pages (CC-licensed, author-attributed).
- Benchmark success criterion: at identical `SourceQuery` the new
  source emits ≥ 10× `n_license_clean` records vs. the single-HTML
  baseline fixture.

## Takeaway for specint

The URL Index is the only way we scale Common Crawl without
scraping. The adapter has to be careful about costs and license
layering, but offline-testable via DuckDB over a 1 MB Parquet
fixture, which is a cheap, high-leverage addition.

[cc-url-index]: https://commoncrawl.org/url-index
[schema-video-object]: https://schema.org/VideoObject
[papers]: ./papers/README.md
