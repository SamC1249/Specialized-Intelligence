# 01 — Wikimedia Commons category traversal

**Status:** proposed (Priority-B in `plan-2026-10-12.md`).
**Hypothesis served:** H2 (yield).

## Problem

The current `WikimediaCommonsSource` searches via
`generator=search&gsrsearch=<terms> filetype:video&gsrnamespace=6`.
That is a *text* search over file metadata; it misses the massive
curated structure that Wikimedia editors have already built around
cooking (`Category:Cooking`, `Category:Food preparation`,
`Category:Culinary techniques`, hundreds of subcats).

## What Commons gives us for free

Three API shapes, all public, no auth:

- `list=categorymembers` with `cmtype=file|subcat`,
  `cmtitle=Category:Cooking`, `cmlimit=500`,
  `continue=...` → enumerate a category.
  Reference: [Commons:API/MediaWiki examples][commons-api].
- `generator=categorymembers` + `prop=imageinfo`
  with `iiprop=url|size|mime|extmetadata` → same walk, but you get
  the imageinfo in one hop.
- `generator=search` with `gsrsearch=deepcat:"Cooking"`
  recursively walks the category graph inside the search backend.
- `fastcci` (Wikimedia Tool Labs) exposes category *intersections*
  server-side (e.g. `Category:Cooking` ∩ `Category:Videos`), avoiding
  client-side graph walks for the common cases.
  Reference: [Commonists/fastcci][fastcci].

## Risks (adversarial)

- **Category pollution.** `Category:Cooking` subtrees contain huge
  volumes of still images, PDFs, and audio. Our filter must enforce
  `mime ∈ {video/*}` *and* keep working if `imageinfo.mime` is
  missing (fall back to extension in `title`).
- **Loops in the category graph.** Commons has known cycles. Either
  cap traversal depth, memoise visited categories, or use fastcci.
- **Deep-cat drift.** `deepcat:` sometimes recurses into unrelated
  categories through weak parent links (e.g. "Cooking" → "Thermal
  physics" → ???). Depth-cap depth=3 and log every subcat we accept.
- **License re-check at the file level.** Being inside
  `Category:Cooking` says nothing about redistribution rights. The
  per-file `extmetadata.LicenseShortName` check must still be the
  gate — categories only influence *discovery*, not license.
- **API etiquette.** MediaWiki wants `User-Agent` and
  ~1 req/s per client; respect `maxlag`. Build in a token-bucket.

## Proposed design

- New file `src/specint/sources/wikimedia_category.py` (keeps the
  original search source untouched for A/B comparability).
- Public API:
  ```python
  class WikimediaCategorySource(BaseSource):
      slug = "wikimedia_category"
      def __init__(self, roots=("Category:Cooking",), max_depth=3, ...)
  ```
- Pure functions:
  - `walk_categories(roots, max_depth, fetch) -> Iterable[str]`
  - `collect_files(categories, fetch) -> Iterable[dict]`
  - `parse(raw, query) -> list[VideoRecord]` (reuses the existing
    `_coerce_license` and `extmetadata` plumbing).
- Fixtures:
  - `tests/fixtures/wikimedia_category/subcat_cooking.json`
  - `tests/fixtures/wikimedia_category/files_page1.json`
  - `tests/fixtures/wikimedia_category/files_page2.json` (continue token)
  - `tests/fixtures/wikimedia_category/adversarial_mixed_mimes.json`
    (contains JPG + PDF + webm so we can assert video-only filter)
- Benchmark success criterion: on an offline synthetic fixture bundle
  with 30 members per category, the new source emits ≥ 10× the
  records of `WikimediaCommonsSource` under the same `SourceQuery`.

## Takeaway for specint

Switching discovery from "text search" to "editor-curated category
graph" is cheap, offline-testable, and aligns with Commons' intended
usage model. It is the single highest-leverage legal-yield move we
have without touching new sources. Ship it before any new source
adapter.

[commons-api]: https://commons.wikimedia.org/wiki/Commons:API/MediaWiki
[fastcci]: https://github.com/Commonists/fastcci
