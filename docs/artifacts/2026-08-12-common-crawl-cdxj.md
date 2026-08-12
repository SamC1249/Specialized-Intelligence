# Artifact — Common Crawl CDXJ index for URL discovery

**Date filed:** 2026-08-12
**Filed by:** Adversarial-Agent
**Primary URL:** <https://commoncrawl.org/cdxj-index>
**Cited in plan:** `docs/plan-2026-08-12.md` (H3)

## One-sentence summary

Common Crawl's **CDXJ index** is a per-crawl file (~300k lines/file,
served from `https://index.commoncrawl.org` or
`s3://commoncrawl/cc-index/collections/`) that lets us enumerate
captured URLs — but *not* filter by schema.org type — so it is the
right primitive for "give me candidate recipe URLs from
`allrecipes.com/*` in the last N crawls" and the wrong primitive for
"give me every page that contains a `VideoObject`."

## Why it matters to us

- The seed `common_crawl.py` adapter has `search()` returning `[]`.
  That's honest but empty. CDXJ closes the yield gap by giving us a
  *discovery* channel that doesn't require full WARC iteration.
- The `cdx_toolkit` Python package (Apache 2.0) handles pagination,
  retries, and S3 or HTTP mirroring, so we do not need to write our
  own client.
- We can bound cost by scoping to (a) permissive-license domains
  (Wikibooks Cookbook, Wikimedia hosts, permissive food blogs) and
  (b) a URL pattern (e.g. `*/recipe/*`, `*/recipes/*`).

## Ideation — how we would consume it

1. Extend `sources/common_crawl.py` with a new helper
   `iter_cdx_urls(host_globs, crawl_ids)` that yields `(url,
   warc_offset, warc_filename)` tuples via `cdx_toolkit`.
2. Add a second helper `fetch_html_from_warc(warc_ref)` that reads a
   single record — but *only* under `SPECINT_RUN_INTEGRATION=1`.
3. The unit test stays offline: feed a checked-in mini-CDXJ line
   directly to `iter_cdx_urls` via `io.StringIO`, assert we correctly
   split fields.
4. Emit a `common_crawl_cdx` row in the compare harness.

## Risks

- CDXJ files are per-crawl and each is ~200GB total. Never download
  the whole index; always use the range API.
- CDXJ carries no schema-type info, so we still pay for HTML fetches
  to confirm each URL contains a `VideoObject`. Pair with WDC (see
  `2026-08-12-web-data-commons-schema-recipe.md`) to shortcut that.
- CDX Server API is rate-limited (documented in the CC docs). Our
  live-mode adapter must back off gracefully.

## Related work

- Common Crawl blog post on CDXJ (2024 revamp): <https://commoncrawl.org/blog/august-2024-newsletter> (see "CDXJ" section).
- `cdx_toolkit`: <https://github.com/cocrawler/cdx_toolkit>.
- Whirlwind tour Jupyter notebook cited from the CDXJ index page.
