# Legal video corpora — what we can and cannot use

_Adversarial-Agent, 2026-07-11_

## Question

Which large, "obvious" cooking / procedural video corpora survive our hard
constraint ("no paid, no ToS violation, no NC/ND")? What licensed sources
are we currently leaving on the table?

## The famous procedural-video corpora are mostly not usable as-is

- **EPIC-KITCHENS-100** (Bristol) is released under
  **CC-BY-NC 4.0** — "You may not use the material for commercial
  purposes." Commercial licenses are gated on emailing
  `uob-epic-kitchens@bristol.ac.uk`. This dataset is a research-only
  reference: any model we train on it inherits an NC restriction and
  therefore is off-limits for a frontier training corpus that we might
  later ship commercially.
  Source: <https://epic-kitchens.github.io/2025.html>
- **Ego4D** (Meta / consortium) grants use "for commercial or
  noncommercial product development" but only after a signed
  bilateral license agreement per organisation, and only to
  "Approved Licensees". This is not a permissive public license — it is
  contract-gated distribution. We keep it in a `RESTRICTED` bucket:
  URL provenance is fine to store; media redistribution is not.
  Source: <https://ego4d-data.org/pdfs/Ego4D-Licenses-Draft.pdf>
- **HowTo100M** is a list of YouTube URLs; the underlying videos'
  licenses are whatever the uploader chose, typically the default
  YouTube Standard License (all rights reserved). Treat as
  `RESTRICTED` unless individually confirmed to be `videoLicense=creativeCommon`.

**Implication.** These are useful *evaluation* baselines and useful
sources of taxonomies (EPIC's 97 verb / 300 noun classes are a gift),
but they cannot be part of the harvest step of our pipeline. Do not
regress on the AGENTS.md hard constraints just because a dataset is
"famous".

## Untapped, permissively-licensed sources we should add

1. **Europeana Search API** — `reusability=open` returns only CC0 /
   CC-BY / CC-BY-SA / Public Domain records; `type=VIDEO` restricts to
   video. Requires a free API key. Cultural heritage skew (traditional
   cooking, historical food-preparation films) is exactly the tail
   we're missing.
   Source: <https://europeana.atlassian.net/wiki/spaces/EF/pages/2385739812/Search>
2. **Openverse API** — currently indexes images and audio, not video.
   Not a direct video source, but useful for cross-license enrichment
   metadata; keep watching.
3. **Vimeo CC-licensed filter** — no first-party JSON API for the
   Creative Commons filter, but the search URL is parameterizable
   (`license=by`, `license=by-sa`, ...). If we want to use it, we must
   scrape *page HTML* respectfully within Vimeo's ToS. Lower priority.
4. **PeerTube language expansion** — we ship 3 English-leaning
   instances today. Add French (Framatube specialty), German
   (video.tchncs.de), Spanish (peertube.cpy.re), and Japanese instances
   for multilingual coverage.
5. **Community Video / Prelinger on Internet Archive** — targeted
   `collection:opensource_movies` and `collection:prelinger` queries
   return CC/PD instructional and educational film.

## Provenance ranking (highest signal first)

| Source                        | Yield (est.) | License integrity | Multilingual  |
| ----------------------------- | ------------ | ----------------- | ------------- |
| Wikimedia Commons             | Medium       | High              | High          |
| Internet Archive (filtered)   | High         | Medium (page-level) | Medium      |
| PeerTube (federated)          | Low-medium   | High (per video)  | Medium-high   |
| Common Crawl JSON-LD recipes  | Very high    | Low (page-level)  | Very high     |
| Europeana `reusability=open`  | Low-medium   | High              | Very high     |
| YouTube CC filter             | High (illusory — many mis-tag) | Low | High |

Every "high yield" cell above is a warning label: unlabelled data is
easy, defensible license attribution is not.

## Action items feeding into today's plan

- Add Europeana as source #5, guarded by API key env var. Keep offline
  parser + fixture in-repo.
- Extend PeerTube instance list to at least one non-English instance,
  add per-instance language priors.
- Add adversarial fixtures for CC-BY-NC and CC-BY-ND items on Wikimedia
  and Archive.org — regression test that we never misclassify these as
  `redistributable`.
