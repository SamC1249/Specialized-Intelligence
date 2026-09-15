# cc-warc-columnar-index — how to shard Common Crawl for VideoObject harvesting

Source: [Common Crawl "get started"](https://commoncrawl.org/get-started),
[Web ARChive (WARC) format blog post](https://commoncrawl.org/blog/navigating-the-warc-file-format),
plus the columnar CC-Index Athena schema documented at
[commoncrawl.org/columnar-index](https://commoncrawl.org/columnar-index-table).

## The problem with our current `common_crawl` adapter

`src/specint/sources/common_crawl.py` has a working `parse(raw)` but its
`search(query)` returns `[]`. The docstring says "Live WARC iteration is
out of scope for the seed PR." Landing a real `search()` would require
scanning tens of TB of WARC per monthly crawl, which is neither cheap
nor fast.

## The columnar index makes it cheap

Common Crawl publishes a Parquet-backed columnar index at
`s3://commoncrawl/cc-index/table/cc-main/warc/`. Schema (relevant
columns):

- `url_host_name` — the fully-qualified host that served the response.
- `url_host_tld` — top-level domain.
- `content_mime_type` — MIME reported by the origin. `text/html` is the
  vast majority.
- `content_languages` — declared languages.
- `warc_filename`, `warc_record_offset`, `warc_record_length` — the
  byte-range to fetch to recover the raw record.
- `crawl` — partition key, e.g. `CC-MAIN-2026-30`.

Athena / DuckDB / Spark can filter this table in constant time per
partition; a full-crawl scan against a well-chosen predicate costs
approximately a few dollars per crawl in cloud egress, which is well
under our zero-cost bar for a *planning* run because DuckDB can query
the public bucket directly from a laptop.

## Sharded harvest strategy

1. **Host allowlist (offline, one-time).** Compile a static allowlist of
   hosts that historically emit `schema.org/VideoObject` on recipe pages
   (Wikibooks mirrors, PBS cooking, government cooking outreach pages,
   university extension services). Store as
   `src/specint/sources/cc_hosts_allowlist.txt`.

2. **Columnar query (offline).** For each `CC-MAIN-YYYY-WW`:

   ```sql
   SELECT warc_filename, warc_record_offset, warc_record_length, url
   FROM ccindex
   WHERE crawl = 'CC-MAIN-2026-30'
     AND subset = 'warc'
     AND content_mime_type = 'text/html'
     AND url_host_name IN (SELECT host FROM allowlist)
   ```

3. **Random-access WARC pull.** For each matching row, HTTP-range-fetch
   the byte slice from `https://data.commoncrawl.org/{warc_filename}`
   (public, no AWS creds needed) using `warcio.ArchiveIterator`. This
   is the exact recipe the Common Crawl blog documents.

4. **Existing parse path.** Feed the extracted HTML to
   `parse_recipe_html()` unchanged. `VideoObject` + `Recipe` JSON-LD is
   already handled.

## Why this respects our hard constraints

- **No paid data.** The columnar index and WARCs are public. AWS egress
  from `us-east-1` to CloudFront is free for the requester.
- **Provenance.** `warc_filename` + `warc_record_offset` + `content_hash`
  is a fingerprint that survives re-crawls. Stored in
  `Provenance.query` today; consider promoting to a first-class field.
- **Legal.** Common Crawl's own terms allow bulk metadata extraction.
  The *content* license is per-page and enforced by our existing
  `combine()` least-privilege rule (see PR #45).

## How we'd use it here (Coding-Agent follow-up)

- **`src/specint/sources/common_crawl.py`** — extend `search()`:
  - If `SPECINT_RUN_INTEGRATION=1`, run the DuckDB query against the
    public bucket, then range-fetch each hit and pipe through
    `parse_recipe_html()`.
  - If not, keep the current no-op (fixture-only) behaviour.
- **`src/specint/sources/cc_hosts_allowlist.txt`** — versioned host
  allowlist, initially populated from Web Data Commons' 2024 top-
  `schema.org/Recipe` hosts. Each host has a comment explaining why it
  is on the list.
- **`tests/fixtures/common_crawl/columnar_index_sample.parquet`** — a
  10-row Parquet fixture that exercises the query path without hitting
  S3. Uses DuckDB in-process.

## Out of scope entirely

- Scanning the *whole* crawl (i.e. no allowlist). That's how you end up
  with a Terabytes-per-day pipeline and an accidental copyright
  problem. The allowlist is what keeps us both legal and cheap.
