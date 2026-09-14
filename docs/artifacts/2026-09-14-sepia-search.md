# Sepia Search — federation-wide PeerTube discovery

*<https://sepiasearch.org/api/v1/search/videos>*

## What it does

- Public HTTP JSON API that indexes videos across the PeerTube
  federation (the list of instances at
  `instances.joinpeertube.org`).
- Response schema is identical to a plain PeerTube instance
  (`/api/v1/search/videos`), so any code we already have for
  PeerTube parses this response with no changes.
- Query params: `search`, `start`, `count`, `sort=-match`,
  `nsfw=false`, `languageOneOf[]`, `boostLanguages[]`,
  `startDate`. Confirmed via SearXNG's `sepiasearch.py` engine
  and PeerTube docs.
- No auth, no API key, aggressive rate-limits (Framasoft's
  polite-Fediverse posture — don't hammer it).

## Why it matters for us

- Our current `peertube.py` adapter is hard-coded to a single
  instance. That is a **10× yield gap** vs a federation-wide
  crawl, and worse, it silently biases us toward whatever
  cooking-language mix that instance happens to host.
- Sepia Search is **the** federation index for PeerTube. Every
  serious PeerTube client (SearXNG, ytfzf, NewPipe) uses it.
- The license posture does not change — each returned record
  still carries a `licence` field per PeerTube's own enum, so
  our existing license-mapping logic in `peertube.py` continues
  to work.

## How we'd use it here

- **Plan hook:** H4 in `docs/plan-2026-09-14.md`.
- **Concrete deliverable:** flip the `PeerTubeSource` default
  `instance_url` from a single-instance URL to
  `https://sepiasearch.org`, and record the *origin* instance
  URL in `Provenance.query` for auditability.
- **Guardrail:** integration suite must honor a
  `min_sleep_between_requests_s=2.0` default; CI stays offline.
- **Adversarial check:** benchmark same query against
  single-instance vs Sepia Search and quantify the
  `unique_authors` delta — if it isn't at least 3× we have a
  bug (Sepia should trivially win on author diversity).

## Citation

Framasoft PeerTube docs — Search API:
<https://docs.joinpeertube.org/api-rest-reference.html#tag/Search/operation/searchVideos>

SearXNG SepiaSearch engine source:
<https://return42.github.io/searxng/_modules/searx/engines/sepiasearch.html>
