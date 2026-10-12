# 03 — Multi-signal license detection

**Status:** proposed (Priority-C in `plan-2026-10-12.md`).
**Hypothesis served:** H3 (license-signal integrity).

## Problem

Right now, each adapter has its own ad-hoc license classifier:

- `wikimedia._coerce_license` reads `extmetadata.LicenseShortName`.
- `archive_org._license_from_url` greps `licenseurl` substrings.
- `peertube._peertube_license` looks up a numeric id.
- `common_crawl.parse_recipe_html` just sets `UNKNOWN` by default.

That is four different confidence stories packed into one coarse enum
with no provenance about *why* the classifier chose that value. On
Common Crawl in particular we have many redundant signals in the same
HTML page and we throw almost all of them away.

## What the C5 project teaches us

[`BramVanroy/CommonCrawl-CreativeCommons`][c5] (aka C5) built a
Creative-Commons-filtered dataset by parsing each page into a tree
and recording, for every license evidence:

- the HTML element it came from (`meta`, `link`, `a`, JSON-LD),
- whether it was in `<head>` or in `<footer>`,
- the license abbreviation and version it decoded to,
- a confidence rank derived from element type and location.

Their observation is that `meta[name="DC.rights"]` or JSON-LD
`license` in `<head>` is dramatically more trustworthy than a random
`<a href="...creativecommons.org/...">` footer link that may just be
discussing CC in general.

## Proposed design

New package `src/specint/licensing/` with:

```
src/specint/licensing/
  __init__.py
  signals.py     # LicenseSignal dataclass: source_tag, location,
                 # evidence_text, raw_url, parsed_license, confidence
  detectors.py   # pluggable rules; returns list[LicenseSignal]
  consolidate.py # pick a winning License from a list[LicenseSignal]
                 # using a documented preference order
```

Preference order (concrete, overridable):

1. JSON-LD `VideoObject.license` on the exact `@id` we chose
   (confidence 0.95).
2. JSON-LD any-type `license` on the same page (0.85).
3. `<meta>` tags in `<head>`: `DC.rights`, `og:license`,
   `article:license` (0.85).
4. `<link rel="license" href="...">` in `<head>` (0.80).
5. CC rdfa island `xmlns:cc` + `cc:license` (0.75).
6. `<a>` tag inside `<footer>` with a creativecommons.org href (0.60).
7. Fallback: regex-match a CC URL anywhere in `<body>` (0.30).

Enum additions on `VideoRecord`:

- `license_confidence: float` ∈ [0, 1], attached by the consolidator.
- `license_signals: list[LicenseSignal]` on `Provenance` (frozen).

## Risks (adversarial)

- **Classifier over-promises.** A high confidence number is itself a
  claim. We MUST test on adversarial fixtures where the "right"
  answer is `UNKNOWN` and assert the consolidator does not round up.
- **Multilingual tags.** `DC.rights` content can be free-text in any
  language; "Dieser Inhalt steht unter einer Creative Commons" is a
  signal; "All rights reserved" in Japanese must *also* parse as
  `RESTRICTED`.
- **Classifier drift between sources.** Keep the per-source legacy
  mapping as the first-ranked signal for Wikimedia / Archive.org /
  PeerTube to avoid regressing their current baseline.

## Takeaway for specint

License is the hard constraint of this project; a single-field
classifier with no confidence is irresponsible at scale. A
provenance-preserving multi-signal detector lets `Reviewer-Agent`
audit decisions without re-running the pipeline, and lets us add a
`--min-license-confidence 0.8` CLI knob to tune the yield/safety
Pareto rather than argue about it.

[c5]: https://github.com/BramVanroy/CommonCrawl-CreativeCommons
