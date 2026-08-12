# Artifact — Web Data Commons Schema.org Recipe corpus

**Date filed:** 2026-08-12
**Filed by:** Adversarial-Agent
**Primary URL:** <https://webdatacommons.org/structureddata/schemaorg/>
**Cited in plan:** `docs/plan-2026-08-12.md` (H3, "yield ceiling")

## One-sentence summary

Web Data Commons (WDC) extracts every `schema.org/*` block out of
Common Crawl, publishes the results as **class-specific N-Quad
subsets** (Recipe is one of them) plus a **Schema.org Table Corpora**
(2023 release: 5M relational tables, ~653M rows across 44 entity
types). This is the *best legal shortcut* to the Recipe long-tail
without our own WARC pipeline.

## Why it matters to us

- Cooking video ↔ Recipe pages are strongly coupled: any recipe page
  containing an inline `VideoObject` block is a candidate for
  world-model training, provided the page license allows redistribution
  (or, minimally, allows us to point at the video URL).
- WDC does the expensive parsing (Any23, 250 AWS spot instances × ~4600
  machine-hours for the 2023 release). We only need to (a) filter to
  Recipe rows that co-occur with VideoObject and (b) recover license
  metadata.
- The corpus is class-*specific*, so we can download only the Recipe
  subset (a few hundred GB N-Quads) instead of the full 97-billion
  triple raw dump.

## Legal surface

- **License to the corpus itself:** WDC releases data extracted from
  Common Crawl. Common Crawl's terms allow "any use" of the extracted
  data. WDC's aggregate is typically re-released under the same terms
  (they cite the CC data provider on each row's fourth N-Quad element).
- **License to the underlying recipe/video content:** *not* granted by
  WDC. This is the whole game. Our adapter must classify each row's
  page domain against a permissive license (Creative Commons, public
  domain, self-declared open). WDC does not do this — but the corpus
  preserves the source URL, so we can re-visit robots.txt / DC
  metadata for a small allowlist of domains (e.g. `wikibooks.org`
  cookbooks, `commons.wikimedia.org`, permissively-licensed food-blog
  archives).

## Ideation — how we would consume it

1. Ship a `sources/webdatacommons_recipe.py` adapter whose `parse()`
   takes a single N-Quad line (or an already-materialised
   `{page_url, recipe: {...}}` dict) and emits a `VideoRecord` only
   when *both*:
   - the row's `@type` includes `Recipe`,
   - the row's tree also contains a `VideoObject` with a
     `contentUrl`/`embedUrl`.
2. Ship a helper `WDCPageLicenseClassifier` that keeps a small
   allowlist of domains known to be permissive (Wikibooks Cookbook,
   Wikimedia, `learn.food-freedom.org`, etc.). Every other row is
   `License.UNKNOWN` and *not counted* as license-clean.
3. Add a benchmark row in `compare/` — `wdc_recipe` — with the same
   fields as the current adapters. Expected: high `n_records`, low
   `n_license_clean` ratio, but the absolute count of license-clean
   rows should exceed direct MediaWiki search for `filetype:video`.
4. **Ship a fixture** with a redacted synthetic N-Quad blob (10–20
   lines) so the unit test does not need any network at all.

## Risks

- WDC releases are **annual**. If we depend on them we lock into a
  yearly cadence for freshness. Mitigation: pair with the CDXJ adapter
  (see `2026-08-12-common-crawl-cdxj.md`) for a monthly refresh path.
- Domain allowlisting is easy to under- and over-fit. Start small.

## Related work

- Bizer et al., *WDC Schema.org Table Corpora*, WWW 2024 companion
  (<https://doi.org/10.1145/3589335.3651441>).
- Common Crawl mailing list thread on adding schema types to the CDX
  index (they *cannot*, so WDC is the workaround):
  <https://groups.google.com/g/common-crawl/c/o60qTmtXoc0>.
