# Artifact: Legal-yield model per source (2026-08-18)

A back-of-envelope model for how many redistributable **cooking-video
hours** we can plausibly harvest per source per crawl-day, given the
current pipeline. Cited numbers are order-of-magnitude, not audited.

## 1. Wikimedia Commons

- Cooking-video categories enumerated by hand (2026-08-18):
 - `Category:Videos_of_cooking` — 74 files.
 - `Category:Home_cooking` — 190 files (mix of stills + videos).
 - `Category:Cooking` — 860 files (largely stills).
 - `Category:Cooking_by_country` and language variants — long-tail,
 estimated 300–500 additional videos.
- **Estimated ceiling: 700–1200 videos, ~50–100 h.**
- Bandwidth: MediaWiki API allows 50 results/request, no daily
 quota below `~5000 req/day` for anons. A single crawl-day can
 fully enumerate the corpus. Yield beyond Day 1 is roughly zero
 (weekly new-file rate is low single digits).
- **Adversarial takeaway:** Wikimedia is a *finite* source. Do not
 base long-term yield forecasts on any linear extrapolation from
 today. It's a fixed asset we should crawl once and then monitor
 with `RecentChanges` diffs.

## 2. Internet Archive

- `mediatype:movies` returns O(10⁶) items overall. Filtering by
 `licenseurl:*creativecommons*` narrows to O(10⁵). Further filtering
 by cooking/recipe/food/knife/kitchen keywords is expected to yield
 O(10³–10⁴) items.
- Duration distribution is bimodal: short user clips (< 5 min) and
 long uploaded TV recordings (30 min – 4 h).
- **Estimated ceiling: 1000–5000 videos, 500–2000 h** (many mid-length).
- Bandwidth: advancedsearch.php returns up to 10 000 rows/query with
 cursor pagination; not rate-limited for reasonable use.

## 3. PeerTube federation

- 3 seed instances currently (`framatube.org`, `video.blender.org`,
 `tilvids.com`). Framatube dominates volume; blender & tilvids are
 curated.
- Cooking is a small niche on PeerTube. Estimated 200–800 CC-clean
 cooking videos across the federation, ~50–200 h.
- **Adversarial takeaway:** the federation is small enough that
 *exhaustive* per-instance enumeration is feasible. Ranking by
 "instance discoverability" is more useful than keyword search.

## 4. Web Data Commons ▶ replace `common_crawl.py` live-search

Web Data Commons (`webdatacommons.org/structureddata/schemaorg/`) has
been extracting every `schema.org/*` block from Common Crawl since
2013 and republishing them as class-partitioned N-quads dumps. The
`VideoObject` and `Recipe` subsets are typically a few GB each per
CC snapshot.

- **Yield estimate:** the 2019 WDC snapshot reported > 10 M
 `VideoObject` blocks. Filtering by `license` field being present
 and pointing at a Creative Commons URL (`creativecommons.org/…`),
 we conservatively estimate **10⁴–10⁵** CC-clean video pointers
 across all domains, of which cooking is O(10³–10⁴).
- **Blueprint for `sources/webdatacommons.py`:**
 1. `parse(raw: bytes) -> list[VideoRecord]` where `raw` is an
 N-quads chunk. Each quad `<subject> <predicate> <object> <graph>`
 tells us either an entity type, a licence, or a metadata field.
 2. Group quads by subject IRI. Retain only subjects with
 `rdf:type = schema:VideoObject` **and** a
 `schema:license` predicate whose object URI matches a CC / PD /
 CC0 pattern.
 3. Emit one `VideoRecord` per surviving subject with
 `license` populated from the URI, `provenance.query =
 "webdatacommons:<snapshot-name>"`, and `media_url = None` (WDC
 doesn't guarantee the contentUrl is reachable — treat it as a
 pointer).
 4. Fixture: check in a hand-authored 200-line N-quads snippet
 covering `{Recipe, VideoObject, Person}` triples.

This adapter should ship **before** we ever iterate a WARC ourselves.
WARCs are 60+ TB per snapshot; WDC dumps are 3-digit GB. Ratio ≈ 10⁴.

## 5. Gold-set methodology

To make the "yield" numbers falsifiable, we need a fixed **gold set**
of 100 hand-verified license-clean cooking videos, stratified across
sources:

```
tests/fixtures/gold/cooking.jsonl  # one VideoRecord per line
```

Construction:

1. Adversarial-Agent (or a human maintainer) hand-picks 25 videos
 per source (100 total), verifying licence and duration by clicking
 through the URL.
2. Each entry stores `id`, `source`, `url`, `license`, and a
 `notes` field describing why it was included.
3. `tests/test_gold_set.py` (future PR) runs `parse()` on the raw
 payload each gold entry's source returns for that video's native
 ID, and asserts:
 - the parser emits at least one record for that native ID,
 - the parser's inferred `license` matches the gold `license`,
 - `duration_s` is within 5% of the gold value.
4. Reports `precision, recall, f1` per source per crawl-day.

Deferred to the next Coding-Agent day — the plan requires it, this
plan does not ship it.

## 6. Yield-report contract

Every crawl-day report under `reports/` should carry:

```
{
  "date": "YYYY-MM-DD",
  "per_source": {
    "wikimedia": {
      "n_records": ...,
      "n_license_clean": ...,
      "total_redistributable_seconds": ...,
      "gold_set_precision": ...,
      "gold_set_recall": ...
    },
    ...
  }
}
```

The critical addition is `total_redistributable_seconds`: today the
harness reports `total_duration_s` including non-redistributable
records, which is not the number we actually optimise.
