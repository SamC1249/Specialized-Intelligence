# wikibooks-cookbook — CC-BY-SA procedural step-text ground truth

Source: [en.wikibooks.org/wiki/Cookbook](https://en.wikibooks.org/wiki/Cookbook)
plus the MediaWiki API at `https://en.wikibooks.org/w/api.php`. All
content is published under **CC BY-SA 4.0** (with GFDL fallback for
older revisions). Wikimedia Enterprise confirms this in
[their Wikibooks API landing page](https://enterprise.wikimedia.com/project-data/wikibooks-api/).

## What the Cookbook is

A collectively-maintained recipe corpus: thousands of pages, each with
an ingredient list, equipment list, step-by-step `recipeInstructions`,
optional `time_phases`, and links to related pages (technique,
ingredient, cuisine). Every page carries a `page_url` + a machine-
retrievable revision id, so provenance is trivial.

Crucially, **it is text-only**. There are no videos on Wikibooks.

## Why this matters for a video corpus

Our current single-source triples look like `(url, license, video
metadata)`. That is the minimum viable record but it is not procedural
supervision.

If we pair a Wikimedia Commons cooking video (which has a title and
often a Commons category) against a Wikibooks Cookbook page (which has
an ingredient list and a numbered step list), we get the *first fully-
legal* `(video URL, step list, ingredient list)` triple in the corpus.
Every constituent piece is redistributable under CC-BY-SA. That is a
qualitatively new record type — closer to the HowTo100M or EPIC-KITCHENS
supervision distribution than anything we currently emit.

## Pairing algorithm sketch

1. Load every Wikibooks Cookbook page via `list=allpages&apnamespace=102
   &apfilterredir=nonredirects` (the `102` namespace is "Cookbook:").
2. Load every Commons video whose title contains a page-title token or
   whose Commons categories intersect the page's `cuisine` /
   `main-ingredient` categories.
3. Emit a `VideoRecord` where:
   - `url` = Commons page URL (video is the primary object)
   - `recipe_steps` = Wikibooks step list
   - `keywords` = Wikibooks tags ∪ Commons categories
   - `license` = intersect(Commons license, `License.CC_BY_SA`) — the
     tighter of the two wins.
   - `provenance.query` = `f"commons:{commons_id};wikibooks:{page_id}"`.
4. The `id` field must include *both* sources so cross-source dedup
   (plan H8) treats them as one logical record. Format:
   `wikimedia+wikibooks_cookbook:{commons_id}+{wikibooks_page_id}`.

## Legal caveat (important)

CC-BY-SA is share-alike. Any downstream corpus that embeds Cookbook
step text is itself CC-BY-SA. This is *fine* for open research
releases but **is not** compatible with releasing a corpus under a more
permissive license (CC-BY, CC0). The `run_comparison` harness should
therefore either:

- Emit the Wikibooks-paired subset under its own license bucket
  (`License.CC_BY_SA`) with a clear reader-visible flag, or
- Drop Wikibooks step-text entirely if the run's target license floor
  is CC-BY or CC0.

Both behaviours must be selectable at CLI time. Add
`--license-floor {CC0,CC_BY,CC_BY_SA}` to `python -m specint compare`.

## How we'd use it here (Coding-Agent follow-up)

- **`src/specint/sources/wikibooks_cookbook.py`** — new adapter,
  `parse(raw)` reads MediaWiki JSON, `search(query)` iterates
  `list=allpages` in the Cookbook namespace with the same
  `SPECINT_RUN_INTEGRATION` gate.
- **`tests/fixtures/wikibooks_cookbook/allpages_recipes.json`** —
  fixture of a small slice.
- **`src/specint/compare/harness.py`** — add a `pair_by_title()` join
  step that consumes Commons + Cookbook streams and yields the
  `(video, steps)` triples described above. Emits a new `paired` slug
  alongside the raw per-source rows.
- **`AGENTS.md`** — extend the Legal Source Allowlist to include
  Wikibooks (already Wikimedia-adjacent; low legal risk). Note it as
  the first text-side source; the video-side sources remain unchanged.
