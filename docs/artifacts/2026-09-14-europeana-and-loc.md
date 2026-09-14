# Europeana + Library of Congress — permissive video sources we are missing

## Europeana

- Aggregates ~4000 European cultural-heritage institutions' digital
  assets, including video.
- **Rights model** is explicit: content is tiered 1–4 based on
  resolution + rights. **Tier 4** = video with `>= 480p` *and*
  rights statement in {`CC0`, `CC-BY`, `CC-BY-SA`, `PDM`
  (public-domain mark)}. This is exactly our redistributable set.
- Public search API: `https://api.europeana.eu/record/v2/search.json`.
  Query with `qf=TYPE:VIDEO&qf=REUSABILITY:open&query=cooking`.
  Requires a free `wskey` (`api2demo` works for evaluation).
- Openverse's frontend already routes video queries here as an
  "external source" — validating that Europeana is the canonical
  free CC video destination outside Wikimedia.

## Library of Congress

- `https://www.loc.gov/search/?fa=original-format:film/video&fo=json`
  returns JSON search results across LoC's ~25 digital film/video
  collections (early cinema, newsreels, gov footage).
- **Rights** are per-item: many are `pre-1928 → public domain` or
  `U.S. government work → public domain`. Adapter must inspect
  `item.rights` and default to `License.UNKNOWN` when not one of
  a small allowed regex set — never optimistic.
- Two-stage fetch: search returns item stubs → item JSON returns
  actual media URLs. Both endpoints are documented and unrated.

## NASA images-api (bonus, same neighborhood)

- `https://images-api.nasa.gov/search?media_type=video` — every
  asset is federal-government public domain.
- Bonus: `/captions/{nasa_id}` returns a WebVTT URL for many
  assets. That is a free, high-signal quality boost for our
  scorer (`has_captions=1`).

## Why they matter for us

- All three are **currently outside our allowlist**, despite fitting
  our legal envelope perfectly. Adding them is pure yield with
  zero risk delta.
- Together they cover:
  - **Europeana** — European cultural / educational video, huge
    cooking-and-craft tail in French / German / Italian.
  - **LoC** — U.S. archival footage; sparse cooking but excellent
    for adjacent "procedural, long-horizon" domains (early
    industrial film, cooking-school reels, home-economics).
  - **NASA** — few cooking clips but rich in *physical-world
    footage with WebVTT captions* — the kind of data V-JEPA-2's
    physical-reasoning benchmarks (CausalVQA) reward.

## How we'd use it here

- **Plan hook:** H3 in `docs/plan-2026-09-14.md`.
- **Concrete deliverables:**
  - `src/specint/sources/europeana.py`
  - `src/specint/sources/loc.py`
  - `src/specint/sources/nasa_images.py`
  Each ships with an offline JSON fixture and a `parse()` unit
  test, mirroring the existing four adapters.
- **AGENTS.md update:** the "Legal Source Allowlist (current)"
  section must gain these three entries in the same PR that adds
  the adapters. This is the only way we honor the rule "Anything
  else requires an entry in the next adversarial plan justifying
  inclusion" — this file is that justification.
- **Benchmark contract:** each new adapter emits a
  `BenchmarkResult` row that must beat `wikimedia`'s baseline
  `mean_quality` (`0.62`) on cooking terms, else its addition is
  purely for yield/diversity and must be justified in the plan
  summary.

## Citations

- Europeana Content Tier documentation:
  <https://europeana.atlassian.net/wiki/spaces/EF/pages/2060091476>
- LoC search JSON API (via community-maintained adapters):
  `https://www.loc.gov/search/?fo=json`
- NASA images-api docs:
  <https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf>
