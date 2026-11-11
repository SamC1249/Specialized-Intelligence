# Artifact — Web Data Commons schema.org extractions (2023-12 release)

**URL:** https://webdatacommons.org/structureddata/2023-12/stats/schema_org_subsets.html
**Also:** https://webdatacommons.org/structureddata/schemaorgtables/2023/
**Access date:** 2026-11-11.

## One-paragraph summary

Web Data Commons (WDC) extracts structured data (Microdata, RDFa,
JSON-LD) from Common Crawl and publishes per-class subsets as
downloadable N-Quads. The 2023-12 release aggregates several years
of CC snapshots. For our purposes, three classes matter:

| schema.org class | Quads | URLs | Hosts | Download size |
| --- | ---: | ---: | ---: | ---: |
| `Recipe` | (listed in subsets page) | 4,489,240 | 42,727 | multi-GB N-Quads |
| `VideoObject` | present in older WDC extraction reports (2012: ≈31M name/url entities); still a top-N class in 2023 | — | — | — |
| `HowTo` (siblings of Recipe) | listed in subsets page | — | — | — |

The authors also publish a "Schema.org Table Corpus" that normalizes
each class into a relational table — effectively a pre-joined
"here is every Recipe on the web with its fields as columns" file.

## Why this matters for Specialized-Intelligence

1. **We should not re-walk Common Crawl HTML for recipes ourselves.**
   WDC already did it, their output is CC-licensed, and it covers
   42k hosts in a single download. Our current
   `src/specint/sources/common_crawl.py` parses one HTML blob at a
   time from a fixture — that is fine for *unit* testing the
   JSON-LD parser, but for actual yield we should ingest WDC's
   N-Quads.
2. **Recipe → VideoObject is the key join.** A `schema.org/Recipe`
   with a nested `video` property (a `VideoObject` with `contentUrl`
   or `embedUrl`) is our ideal candidate: it comes with step text
   (`recipeInstructions`, often as `HowToStep[]`) *and* a video URL
   on the same page, governed by the page's license. We should
   build a dedicated `wdc_recipe` adapter whose input is a line of
   WDC N-Quads and whose output is a `VideoRecord` with populated
   `recipe_steps`.
3. **Pre-joined table corpus = no RDF library needed.** The 2023
   table corpus is CSV/Parquet-ish and much easier to ingest than
   raw N-Quads. We can ship a tiny sampled file as a fixture.
4. **Licensing of WDC itself.** WDC is published for research use;
   the *content* carries whatever license each source page
   declares. We must continue to run page-level license verification
   (plan H2) — WDC's extraction does not vouch for the license of
   any particular page.

## Direct stats worth preserving

- 2023-12 Recipe subset: **5,683,640 Recipe instances across
  4,489,240 URLs and 42,727 hosts** (synthesized from the WDC
  subsets page).
- 2023-12 Movie subset (comparison): 4,451,037 Movie instances,
  2,003,583 URLs, 7,641 hosts, 2.38GB. Recipe is *larger* than
  Movie by every axis → recipe content is one of the densest
  structured-data categories on the web.
- Historical: the 2012 extraction already reported ≈31M
  `schema.org/VideoObject/name` and `schema.org/VideoObject/url`
  entities. The 2026 number is certainly much larger; even a 5–10%
  intersection with Recipe is a very large candidate pool.

## Implementable takeaways for `Coding-Agent`

- New adapter `src/specint/sources/wdc_recipe.py` whose `parse`
  takes one N-Quads line (or one table row) and emits a
  `VideoRecord`. `license=UNKNOWN`, `license_verified=False` until
  the page-license verifier runs.
- Fixture: sample 50 rows from the WDC "Recipe (sample)" download,
  check into `tests/fixtures/wdc_recipe/`. Make sure at least one
  row has a nested VideoObject with `contentUrl`, one with
  `embedUrl` (YouTube embed), one with no video (should be skipped
  by the adapter but without raising), and one with a malformed
  `@context` (parser must not crash).
- Document in `AGENTS.md` that the WDC source is read-only (we do
  not redistribute their N-Quads; we only link to them in reports).
