# sources-shortlist.md — Candidate adapters, ranked

Scope: adapters we have *not* implemented yet but which plausibly meet
`AGENTS.md`'s legal allowlist. Each entry documents the licence basis,
the API shape, an order-of-magnitude yield estimate, and whether it
belongs in the next PR or a later one.

Ranking is by `(yield × licence-cleanliness × ease-of-offline-test) /
risk`.

| Rank | Source               | Est. clean video hours accessible | Priority | Why                                                                              |
| :--- | :------------------- | :-------------------------------- | :------- | :------------------------------------------------------------------------------- |
| 1    | Europeana API        | 2,000+ (cross-domain)             | **next** | Public API, explicit `reusability=open` filter, cross-domain → generalisation test. |
| 2    | V3C2 (NIST / Vimeo)  | 1,300                             | **next** | Pre-vetted CC-BY Vimeo, shots + keyframes already segmented, data agreement explicit. |
| 3    | Openverse proxy      | n/a (dedup oracle)                | **next** | Enumerates CC search URLs across 5+ providers; our deduplication ground-truth.    |
| 4    | PeerTube federation  | 500+                              | high     | Extend current single-instance adapter to the SepiaSearch federation index.       |
| 5    | NASA Image & Video   | 400 (US gov PD)                   | medium   | Not procedural cooking but PD and camera-rich; generalisation signal.             |
| 6    | USDA cooking videos  | 20 (US gov PD)                    | medium   | Tiny but gold: real cooking content under US-gov public domain.                   |
| 7    | Smithsonian OA       | ~100                              | medium   | CC0 cultural-heritage video; craft/manufacturing proxy.                           |
| 8    | Flickr videos CC     | 300+                              | medium   | API deprecation risk but still live.                                              |
| 9    | NARA (US Nat. Arch.) | 1,000+ (PD, mixed)                | low      | Mostly historical, metadata quality uneven.                                      |
| 10   | YouTube Data API (CC)| 10,000+ (listings only)           | low      | Allowed by `AGENTS.md` for CC-filter *listings*; costs quota, high ToS risk.      |

Yield estimates are *order-of-magnitude only*; every number is a research
question for a nightly-integration run (`docs/plan-2026-10-13.md`
deliverable "Nightly integration workflow"). Record the real yields in
`reports/compare-<source>-<date>.json` as each adapter lands.

---

## A. "Ship next" (promoted into `plan-2026-10-13.md` as deliverables 5–7)

### A1. Europeana — `sources/europeana.py`

- **Endpoint.** `GET https://api.europeana.eu/record/v2/search.json`.
- **Required params.** `wskey=$SPECINT_EUROPEANA_KEY` (free key),
  `type=VIDEO`, `reusability=open`, `rows=100` (max per page),
  `cursor=*` for cursor-based pagination, `query=<terms>`.
- **Response shape.** JSON. Each item has:
  - `edmPreview[*]` — preview URL(s)
  - `edmIsShownBy[*]` — direct media URL
  - `rights[*]` — array of licence URLs (we map URL → `License` enum)
  - `title[*]`, `dcDescription[*]`, `dcLanguage[*]`, `edmTimespanLabel`
  - `europeanaCollectionName[*]` — provenance helper
- **Licence coverage.** With `reusability=open`:
  CC0 / PDM / CC-BY / CC-BY-SA only. `reusability=restricted` adds
  NC/ND — we must set `License.RESTRICTED` and drop `media_url`.
- **Offline fixture.** Save one `search?query=cooking` response and
  one `search?query=surgery` response under
  `tests/fixtures/europeana/`. Target total <64 kB after pretty-print.
- **Owner.** Coding-Agent deliverable 6.

### A2. V3C2 — `sources/v3c2_local.py`

- **Mode.** *Local-only* adapter: no network. Reads a user-provided
  directory of V3C2 JSON metadata files + the master-shot CSV.
  Appropriate because V3C2 is distributed via a data agreement, not
  an API.
- **CLI gate.** `python -m specint compare --only v3c2_local
  --v3c2-root /path/to/v3c2` — if `--v3c2-root` is absent and
  `SPECINT_V3C2_ROOT` env var is unset, the adapter yields zero
  records and emits a `BenchmarkResult.empty` with `notes="v3c2:not-configured"`.
  This keeps CI deterministic.
- **Fixture.** 3 synthetic JSON records + 1 synthetic master-shot CSV
  row, under `tests/fixtures/v3c2_local/`.
- **Owner.** Later Coding-Agent run (after Europeana lands).

### A3. Openverse URL-proxy — `sources/openverse_proxy.py`

- **Mode.** Produces *landing-URL records only* (`media_url=None`,
  `license=UNKNOWN` until a real adapter re-resolves them). Primary
  purpose: dedup oracle across our other adapters.
- **How.** Hard-code the external-source URL builders Openverse uses
  (Vimeo CC filter, Europeana `TYPE:"VIDEO"` + CC rights, Wikimedia
  Commons video type, Flickr CC). For each term in `SourceQuery.terms`,
  emit one record per external search *URL*. The record's `id` is
  `openverse:<provider>:<sha256(query)>`.
- **Fixture.** None needed — the "parse" step is pure URL generation.
  Unit-test deterministic SHA inputs.
- **Owner.** Coding-Agent deliverable 5.

---

## B. "Ship soon" (second PR)

### B1. PeerTube federation (SepiaSearch)

- **Endpoint.** `https://sepiasearch.org/api/v1/search/videos`.
  Federated across ~200 instances. Same response shape as the
  per-instance API we already parse.
- **Delta from current adapter.** Replace single `host` with the
  SepiaSearch host; add `instance_filter` for excluding instances with
  >5% non-CC content historically.

### B2. NASA Image and Video Library

- **Endpoint.** `https://images-api.nasa.gov/search?media_type=video&q=<terms>`.
- **Licence.** 17 U.S.C. §105 — US federal government works are PD.
  Caveat: *some* NASA content comes from contractors and is not PD.
  Mitigation: default `License.PUBLIC_DOMAIN` but drop records whose
  `secondary_creator` matches a known contractor list.

### B3. Smithsonian Open Access

- **Endpoint.** `https://api.si.edu/openaccess/api/v1.0/search?q=<terms>&api_key=$KEY`.
  Free API key required. Filter `online_media_type=Video` and
  `media_usage=CC0`.

### B4. USDA cooking content

- **Endpoint.** Mix of USDA MyPlate and FNS YouTube channel. Most
  USDA material is PD but *delivery* is on YouTube — same ToS caveat
  as any YouTube adapter. Realistic path: metadata-only via YouTube
  Data API with `videoLicense=creativeCommon` *and* channel allowlist.

---

## C. "Argue in a later Adversarial-Agent plan"

### C1. YouTube Data API (CC-filter listings)

- `AGENTS.md` already allows this for *URL + metadata only*. The reason
  it is bottom-of-list: cost + stability. Quota is 10,000 units/day;
  a `search.list` call costs 100 units, so ~100 queries/day. We should
  only turn this on once we have (a) a cost model, (b) a way to merge
  the output into our dedup cascade so we are not reposting the same
  URL dozens of times, and (c) a stance on YouTube API ToS §III.E.2
  (don't aggregate/display API data outside the Service).

### C2. Vimeo API (full, not V3C2)

- Vimeo's API returns licence metadata (`licenses.filter=creative_commons`
  variants). Risk: Vimeo's API ToS is more restrictive than YouTube's;
  requires app review for public use. Defer until a maintainer with a
  Vimeo partner account signs off.

### C3. Nico Nico Douga (NND) CC uploads

- Japanese cooking is dense and under-represented. NND has a `TOS`
  that permits CC-tagged downloads for research with attribution.
  Needs a careful read of §12 before we commit; Adversarial-Agent to
  review in a future plan.
