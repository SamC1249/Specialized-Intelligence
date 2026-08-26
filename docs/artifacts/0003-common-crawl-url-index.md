# 0003 — Common Crawl URL Index as a legal video discovery layer

- Sources:
  - Common Crawl Foundation. *URL Index* (columnar Parquet).
    https://commoncrawl.org/url-index
  - `commoncrawl/cc-index-table` — schema and Spark tooling.
  - `commoncrawl/cc-index-annotations` — how third parties join their
    own annotation tables to the CC URL index (FineWeb-Edu is one
    example).
- Reviewed: 2026-08-26 by Adversarial-Agent.

## What is it?

Common Crawl publishes a **columnar Parquet index** of every URL it
has ever crawled, hosted at
`s3://commoncrawl/cc-index/table/cc-main/warc/`, partitioned by crawl
and subset (`warc`, `robotstxt`, `crawldiagnostics`). Each row carries
`url`, `url_host_name`, `url_host_registered_domain`, `content_mime`,
`content_mime_detected`, `warc_filename`, `warc_record_offset`, and
`warc_record_length` — enough to jump directly to the raw HTML for any
crawled page.

`cc-index-annotations` is an official pattern for joining an
externally-published annotation table (e.g. FineWeb-Edu's per-host
quality score) to that index using SQL/Athena/DuckDB.

## Why it matters

Our current `common_crawl.py` adapter only knows how to parse a single
HTML fixture that already contains a `schema.org/VideoObject` block. To
scale we need a **discovery** layer that answers: *"across the entire
crawl, which pages plausibly contain a permissively-licensed cooking
video?"* — before downloading any HTML.

The URL index gives us a way to do that with **zero live scraping**:

1. Filter `url_host_registered_domain` by an allowlist that includes
   permissively-licensed publishers (allrecipes.com is not on it;
   commons.wikimedia.org, archive.org, and small independent recipe
   blogs that publish under CC-BY are).
2. Filter `content_mime_detected = 'text/html'`.
3. Fetch only the WARC ranges pointed to by the surviving rows — this
   is orders of magnitude cheaper than a fresh crawl and, crucially,
   respects the original crawler's `robots.txt` decisions.

## Implementation ideas for `specint`

1. **`sources/common_crawl_index.py`.** New adapter that takes a
   `SourceQuery` and returns candidate URLs (not yet `VideoRecord`s)
   by running a small DuckDB SQL query against a *checked-in fixture
   Parquet file* in unit tests, and against a user-provided
   `--cc-index-uri` in integration mode.

   ```sql
   SELECT url, url_host_registered_domain, warc_filename,
          warc_record_offset, warc_record_length
   FROM cc_main_2026_XX
   WHERE content_mime_detected = 'text/html'
     AND url_host_registered_domain IN (SELECT host FROM allowlist)
     AND (
       lower(url) LIKE '%/recipe/%'
       OR lower(url) LIKE '%/cook/%'
       OR lower(url) LIKE '%/video%'
     )
   LIMIT :max_results
   ```

2. **License-first host allowlist.** Move the hard-coded allowlist out
   of Python into `data/allowlist_hosts.tsv` (host,
   default_license_tier, verified_by, verified_at). Every host must be
   accompanied by a human-checked source (Terms page URL, a specific
   footer, or an explicit CC declaration). CI parses this file and
   fails if `verified_by` is empty or `verified_at` is older than
   365 days.

3. **Two-stage adapter shape.** Rename the current adapter to
   `common_crawl_html.py` (parses HTML given raw bytes). The new
   `common_crawl_index.py` is stage 1 (candidate discovery). The
   comparison harness gets a new `notes` field per row that names the
   stage. Yield is reported per stage: `n_candidate_urls`,
   `n_html_bytes_kb`, `n_video_records`.

4. **Explicit fallback for JSON-LD lies.** The seed plan already
   flags that `contentUrl` in JSON-LD may point to a third-party
   video host with an incompatible license. Enforce this in the
   parser: if `contentUrl.host` is not in the allowlist, either
   demote to `License.UNKNOWN` or drop `media_url` entirely (keeping
   the record for citation/URL provenance only).

## Benchmark row that would prove it

Two new rows per crawl-month:

```
source                       stage          n         cost_estimate_usd
common_crawl_index           candidates     ?         ~$0 (index scan)
common_crawl_html            records        ?         (bytes / 1e9)*$0.09
```

Comparison target: at least 10× the yield-per-dollar of the current
`common_crawl` HTML-fixture adapter, otherwise the added complexity is
not justified.

## Constraints & risks

- CC index scans are cheap only from AWS us-east-1. Off-cloud scans
  pay bandwidth. Document this in the CLI help.
- The columnar schema evolves; pin a specific crawl-month per
  benchmark row and record `schema_version` in the notes field.
- Hosts on the allowlist can silently change their license terms.
  The 365-day re-verification rule above is our safety valve.
