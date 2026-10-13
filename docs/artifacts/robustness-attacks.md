# robustness-attacks.md — Adversarial fixtures the Coding-Agent must add

Today each `parse()` has **exactly one happy-path fixture**. That means
every parser has an undiscovered class of inputs that will either (a)
raise and crash the harness, or (b) silently produce
mis-licensed/mis-measured records. The latter is worse: it looks like
yield.

This document enumerates the attacks per adapter, the fixture file name
to use, and the invariant each attack is checking. Fixtures are *data,
not tests* — the test code lives in each adapter's existing
`test_sources_*.py`, parametrised over the attack list.

The list below is deliberately short enough to implement in one PR, and
each attack is traceable to a *real-world* failure mode we have
observed in CC-licensed data.

## Universal invariants

Every parser, on every fixture, must satisfy:

1. **Return type is `list[VideoRecord]`.** Never `None`, never a
   generator, never raise `TypeError` on an upstream payload shape
   change.
2. **Every record validates as `VideoRecord`.** No partial dicts, no
   bare strings.
3. **`provenance.extractor` matches the module path.** Easy
   anti-pattern: copy-pasting another adapter's provenance.
4. **`license == License.RESTRICTED` ⇒ `media_url is None`.** The
   schema allows `media_url` to be set, but our redistribution contract
   forbids it for restricted licences. Must be enforced in the adapter,
   not downstream.
5. **`license == License.UNKNOWN`** is acceptable *per record* but
   each adapter must never return a run of >50% UNKNOWN records on a
   query — if it does, the adapter's licence classifier is broken.
   (Threshold check lives in `tests/test_contract.py`, not the per-adapter test.)

---

## Wikimedia Commons (`sources/wikimedia.py`)

| Fixture                                              | Attack                                                                | Expected                                                                                     |
| :--------------------------------------------------- | :-------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| `wikimedia/search_empty.json`                        | `{"query": {"pages": {}}}` — API returned no pages                    | Returns `[]`, no exception.                                                                  |
| `wikimedia/search_non_video.json`                    | Page is `image/jpeg` (user searched a term that matched images)       | Returns `[]`.                                                                                |
| `wikimedia/search_missing_license.json`              | `imageinfo[0].extmetadata` has no `LicenseShortName`                  | Returns a record with `license=UNKNOWN`, `media_url=None`.                                   |
| `wikimedia/search_cc_by_nc.json`                     | `LicenseShortName.value = "CC BY-NC 4.0"`                             | Returns a record with `license=RESTRICTED`, `media_url=None`.                                |
| `wikimedia/search_duration_as_string.json`           | `imageinfo[0].duration = "123.4"` instead of float                    | Either coerces to float, or sets `duration_s=None`. Never crashes.                           |
| `wikimedia/search_truncated.json`                    | File is `{"query": {"pages":` (truncated JSON)                        | Caller handles — parser receives already-decoded dict so this is actually a harness-level test. |

## Internet Archive (`sources/archive_org.py`)

| Fixture                                              | Attack                                                                | Expected                                                                                     |
| :--------------------------------------------------- | :-------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| `archive_org/search_empty.json`                      | `{"response": {"docs": []}}`                                           | Returns `[]`.                                                                                |
| `archive_org/search_no_license.json`                 | `doc.licenseurl` missing                                              | Returns record with `license=UNKNOWN`.                                                       |
| `archive_org/search_cc_by_nd.json`                   | `licenseurl = "https://creativecommons.org/licenses/by-nd/4.0/"`      | `license=RESTRICTED`, `media_url=None`.                                                      |
| `archive_org/search_bad_date.json`                   | `publicdate = "0000-00-00T00:00:00Z"`                                  | `published_at=None`, record still returned.                                                  |
| `archive_org/search_lies_about_mediatype.json`       | `mediatype = "movies"` but `format = ["JPEG Thumb"]`                   | Parser must inspect `format` list; records with no video format drop.                        |

## PeerTube (`sources/peertube.py`)

| Fixture                                              | Attack                                                                | Expected                                                                                     |
| :--------------------------------------------------- | :-------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| `peertube/search_empty.json`                         | `{"data": [], "total": 0}`                                            | Returns `[]`.                                                                                |
| `peertube/search_license_1_through_7.json`           | 7 records, one per PeerTube licence code (1..7)                        | Correct mapping: 1=UNKNOWN(Attribution), 2=CC_BY, 3=CC_BY_SA, 4=CC_BY_ND, 5=CC_BY_NC, 6=CC_BY_NC_SA, 7=CC_BY_NC_ND. ND/NC codes → `RESTRICTED`. (See PeerTube `licence` enum.) |
| `peertube/search_privacy_private.json`               | `privacy.id = 2` (unlisted) or `3` (private)                           | Parser drops private videos regardless of licence.                                           |
| `peertube/search_isLive_true.json`                   | `isLive = true` and `duration = 0`                                     | Record either dropped (preferred) or marked `duration_s=None`.                              |

## Common Crawl recipe (`sources/common_crawl.py`)

| Fixture                                              | Attack                                                                | Expected                                                                                     |
| :--------------------------------------------------- | :-------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| `common_crawl/recipe_no_video.html`                  | `Recipe` JSON-LD block without `video`                                | Returns `[]`.                                                                                |
| `common_crawl/recipe_nested_video_object.html`       | `Recipe.video` is a nested `VideoObject`                              | Extracts the nested URL + duration.                                                          |
| `common_crawl/recipe_step_videos.html`               | `Recipe.recipeInstructions[*].video` with per-step `Clip`             | Emits one record per step clip when per-step clips are shipped; else aggregates to one.      |
| `common_crawl/recipe_bad_ldjson.html`                | `<script type="application/ld+json">{broken json</script>`             | Returns `[]`, logs warning. No crash.                                                        |
| `common_crawl/recipe_page_restricted_license.html`   | Page has `<meta name="rights" content="all rights reserved">`         | Returns `[]`. (See licence-first filter below.)                                              |

### Licence-first filter

Common Crawl is special: we must consult the *page*'s licence, not the
embedded video provider's. The adapter should read, in order:

1. `<link rel="license" href="...">`
2. `<meta name="rights" content="...">`
3. `schema.org/CreativeWork.license` on the top-level LD-JSON block.

If none of the three is a redistributable Creative Commons URL, the
whole page is skipped — regardless of what the embedded VideoObject
claims. This is encoded in the proposed `common_crawl/recipe_page_restricted_license.html`
fixture.

---

## Fuzz corpus for the shared licence classifier

Once `src/specint/licensing.py` lands (plan deliverable 1), the
following strings/URLs should round-trip through the classifier to the
expected enum. Store as a YAML file so it can be extended without a
code change:

```yaml
# tests/fixtures/licensing/known_strings.yaml
- in: "CC0 1.0 Universal"
  out: CC0
- in: "CC BY 4.0"
  out: CC_BY
- in: "Creative Commons Attribution-ShareAlike 3.0"
  out: CC_BY_SA
- in: "cc-by-sa"
  out: CC_BY_SA
- in: "Public Domain Mark 1.0"
  out: PUBLIC_DOMAIN
- in: "GNU Free Documentation License"
  out: OTHER_FREE
- in: "CC BY-NC-ND 4.0"
  out: RESTRICTED
- in: "https://creativecommons.org/licenses/by-nd/3.0/"
  out: RESTRICTED
- in: "All Rights Reserved"
  out: RESTRICTED
- in: ""
  out: UNKNOWN
- in: null
  out: UNKNOWN
```

Add new strings whenever an adapter encounters an unexpected licence
label; the classifier must stay the single source of truth.

---

## Negative-sample fixtures

A parser can also be wrong by *letting too much through*. For each
adapter add one fixture of a **near-topic false-positive**:

- Wikimedia Commons: `search_music_video.json` — a Bach piano
  performance that matched "cooking" because the uploader wrote "a feast
  for the ears" in the description.
- Internet Archive: `search_karaoke.json` — karaoke track titled
  "Cooking by the Book" (karaoke tracks are everywhere on IA).
- PeerTube: `search_asmr_cooking.json` — ASMR audio with a static
  image track labelled as video.
- Common Crawl: `recipe_slideshow.html` — "recipe" page whose only
  "video" is a looping 2-second GIF.

The quality scorer should produce a score ≤0.3 on each of these. If
not, the scorer weights are wrong and the plan's deliverable 4
(pluggable quality domain) grows a new component.
