# SepiaSearch — federated search across the PeerTube network

- **API endpoint:** `https://sepiasearch.org/api/v1/search/videos`
- **Docs:** <https://docs.joinpeertube.org/api-rest-reference.html#tag/Search/operation/searchVideos>
- **Source:** AGPLv3+, code at
  <https://framagit.org/framasoft/peertube/search-index>
- **Sepia Search overview:** <https://framablog.org/2020/09/22/sepia-search-our-search-engine-to-promote-peertube/>

## Why this matters

Our current `PeerTubeSource` targets a single instance. PeerTube is a
federation of ~800 independent instances (per Wikipedia entry, 2021
count; the number is now larger). Searching one instance covers *its*
locally-hosted videos plus the subset it federates with; searching
SepiaSearch covers the full public federation Framasoft's index tracks.
For our purposes:

- Same JSON schema as the per-instance `/api/v1/search/videos`
  endpoint, so the existing `PeerTubeSource.parse` should work
  unchanged.
- Requires **no API key**, honours a small rate limit.
- Returns a `licence.label` field per video that we can map into our
  `License` enum with the existing helpers.

## Transferable to `specint`

- **New adapter `src/specint/sources/sepiasearch.py`** subclassing
  `PeerTubeSource` and overriding only the base URL. Register it in
  `sources/__init__.py` under slug `peertube_federated`.
- **Cross-source dedup** becomes even more important once federation
  is in play: the same video will show up as (per-instance,
  federated) and possibly across mirrors. Emit a
  `duplicate_of: source_native_id` field.
- **Rate-limit awareness** — SepiaSearch caps at 500 requests /
  15 minutes / IP per the PeerTube docs. Our `client()` factory needs
  to respect a token-bucket configured per-source-slug.
- **Fixture.** Add `tests/fixtures/sepiasearch/search_cooking.json`
  containing at least three real result payloads (with the
  authors' names redacted to placeholders). Unit test parses without
  network.

## NOT transferable

- Per-video licence text from PeerTube is *self-declared* by
  uploaders and may be wrong. We must default to `License.UNKNOWN`
  unless the string maps cleanly (e.g. `"Attribution - ShareAlike"` →
  `CC_BY_SA`).
- Federation includes NSFW instances by default; use
  `nsfw=false` param and (defensively) an allow-list of instance
  hosts populated at run time from `instances.joinpeertube.org`.

## Adversarial notes

1. Federation multiplies apparent yield but not *unique* yield.
   Without dedup we will over-count. The first PR that adds this
   adapter must ship with a dedup report on the fixture set proving
   that duplicates are collapsed.
2. SepiaSearch's own moderation excludes some instances. We should
   audit which instances are excluded and record that decision in
   provenance ("this SepiaSearch fetch missed hosts X, Y, Z").
