# Common Crawl vs Web Data Commons for recipe/video extraction

Date: 2026-08-11  ·  Author: Adversarial-Agent

Our current `src/specint/sources/common_crawl.py` has a `parse()` that
handles a single HTML page and a `search()` that returns `[]`. To
scale, we implicitly assume we will write our own WARC iterator +
JSON-LD extractor. **That is the wrong build**. Web Data Commons
(WDC) has been doing that extraction for over a decade and publishes
class-specific subsets we can consume directly.

## Numbers that decide it

From `webdatacommons.org/structureddata/schemaorg/` and
`.../2023-12/stats/schema_org_subsets.html`:

- WDC latest release (2024-12) is derived from the October 2024 Common
  Crawl corpus: **12.3M PLDs, ~137B quads, 1.7 TB total**.
- The **Recipe** class-specific subset (2023-12 release, most recent
  with per-class stats visible) contains
  **502,684,939 quads across 4,489,240 URLs on 42,727 hosts**, ~8 GB
  compressed. That is orders of magnitude larger than anything we
  could plausibly bootstrap in-house.
- Every `Recipe` node that satisfies Google's `Recipe` markup guidance
  can nest a `VideoObject` in the `video` property, with
  `name`, `description`, `thumbnailUrl`, `uploadDate`, and
  `contentUrl`/`embedUrl` — exactly the fields our `VideoRecord`
  needs.

## Extraction path

1. Pull the WDC Recipe subset chunk files (N-Quads). Each chunk is a
   few hundred MB; no auth, no rate limiting.
2. Group quads by subject IRI to reconstruct `Recipe` and
   `VideoObject` nodes.
3. Filter to nodes whose enclosing PLD is on our per-page license
   allowlist (see `2026-08-11-license-taxonomy.md`).
4. Emit `VideoRecord`s with `source="wdc_recipe"`,
   `provenance.query = "wdc-<release>-<chunk>"`.

## Why not raw Common Crawl?

- CDX index does not carry schema.org metadata — you have to fetch
  the full WARC record to see if a page contains a `Recipe`. That's
  ~100 KB per candidate page vs ~200 bytes per WDC quad.
- Even at Athena speeds, the SQL-join-then-byte-range-fetch pattern
  (see `commoncrawl/cc-notebooks/cc-index-table`) is best suited to
  targeted URL lookups, not domain-scale schema mining.
- WDC has already deduplicated and canonicalized JSON-LD contexts,
  which is fiddly to reimplement.

## Failure modes to guard against

- **WDC is refreshed only ~yearly.** Any pipeline relying on it will
  lag mainstream Common Crawl by up to 12 months. Combine with live
  Common Crawl only for the latest month if freshness matters.
- **Schema.org licence claims are frequently wrong or absent.** WDC
  does not license-filter for us. We must apply our per-PLD allowlist
  (Wikibooks, USDA / MyPlate.gov, some CC food blogs, etc.) instead
  of trusting node-level `license` triples.
- **Nested `VideoObject.contentUrl` often points to YouTube.** Those
  hits must be re-routed to the YouTube-CC adapter, not treated as
  redistributable directly from the recipe page.

## Implications for specint

- **Add** `src/specint/sources/wdc_recipe.py` that consumes a fixture
  N-Quads chunk in unit tests; live download is a separate opt-in
  path (`SPECINT_WDC_LIVE=1`).
- **Keep** the existing `CommonCrawlRecipeSource` but rename its role:
  it becomes an "HTML page → VideoRecord" utility that both the WDC
  adapter *and* a future live WARC iterator can call. This preserves
  its unit tests and avoids code duplication.
- **Do not** attempt to reproduce WDC's extractor. Cite WDC in
  provenance so downstream users can verify.

## References

- WDC schema.org series: `https://webdatacommons.org/structureddata/schemaorg/`
- WDC Recipe subset stats (2023-12):
  `https://webdatacommons.org/structureddata/2023-12/stats/schema_org_subsets.html`
- Google Recipe structured data guidance:
  `https://developers.google.com/search/docs/appearance/structured-data/recipe`
- `commoncrawl/cdx_toolkit` (`https://github.com/commoncrawl/cdx_toolkit`)
