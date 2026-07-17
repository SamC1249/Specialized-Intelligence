# NARA + USDA + Prelinger: public-domain film archives we do not yet crawl

## Legal basis

- **17 U.S.C. §105** — works of the U.S. federal government are not
  copyrightable in the United States. Every film in the NARA Motion
  Picture, Sound, and Video collection produced by a federal agency
  (USDA, Department of War, HHS, NASA, USIA, etc.) is
  `License.PUBLIC_DOMAIN` by default.
- **Prelinger Archives** — Rick Prelinger's personal collection of
  ephemeral sponsored / educational / amateur film, held physically
  in San Francisco and mirrored on Internet Archive under
  `collection:prelinger`. Approx. **65 %** of the collection is in
  the public domain by expired copyright or missing renewal.
  Prelinger routinely donates his items PD; when an item's
  `licenseurl` is empty on IA, that's the intent.

## Corpus we're not touching

### NARA highlights (cooking / food-prep only)

- *A Step-Saving Kitchen* (1949, USDA Bureau of Human Nutrition
  and Home Economics) — 13:36, U-shaped kitchen demo, narrated by
  home economist Lenore Sater. NARA identifier 1783 / local
  identifier 16-P-1045, also mirrored at IA as
  `stepsavingukitch646unit_0` (though that IA record is the
  companion pamphlet, not the film).
- *Public Information and Training Motion Picture and Television
  Productions* series (Record Group 16) — 1,300+ films from USDA
  Office of Public Affairs, at least ~100 of which are kitchen /
  cooking / preservation focused (Bureau of Human Nutrition and
  Home Economics, Extension Service, Food Safety and Inspection
  Service).
- USDA food-safety and canning films from the 1930s-1950s (Bureau
  of Home Economics, e.g., *Home Canning*, *Freeze Your Own Foods*).

### Prelinger highlights on Internet Archive

- `Kitchen-Come-True` (1946), *Aunt Sammy's Radio Recipes* radio
  transcriptions, *Design for Dreaming* (1956) — food & home
  economics ephemera.
- Aggregate `collection:prelinger AND (cooking OR kitchen OR recipe
  OR food)` returns >200 items today, most PD.

## Access mechanics

### NARA Catalog API

- Endpoint: `https://catalog.archives.gov/api/v2/records`
- Auth: none required for read; API key optional but not enforced.
- Response format: JSON per the *NARA Catalog API v2* spec (2024).
- Rate limit: 100 req/min per IP (documented, not aggressively
  enforced).
- Fields we care about: `naId`, `title`, `descriptionText`,
  `productionDates`, `variantControlNumberArray`, `digitalObjects[]`
  (media URLs + MIME types), `generalNoteArray`.
- License field is *implicit* — always PD for federally-produced
  items. Explicit `useRestrictionArray` should be checked and
  demoted if non-empty.

### Prelinger on Internet Archive

- Endpoint: our existing `sources/archive_org.py`, with a
  `collection:prelinger` query pin. Same JSON schema as our current
  fixture.

## Concrete adapter shapes

```python
# sources/nara.py (offline-parseable)
class NARASource(BaseSource):
    slug = "nara"
    def search(self, query): ...  # network path; offline: not exercised
    def parse(self, raw: dict, query: SourceQuery) -> list[VideoRecord]:
        # raw is a NARA Catalog v2 records response JSON blob
        # default license = PUBLIC_DOMAIN unless useRestrictionArray non-empty
```

```python
# sources/prelinger_on_ia.py
class PrelingerSource(ArchiveOrgSource):
    slug = "prelinger"
    default_query_extras = 'collection:prelinger'
    def parse(self, raw, query):
        records = super().parse(raw, query)
        for r in records:
            if r.license is License.UNKNOWN and not r.license_url:
                r = r.model_copy(update={"license": License.PUBLIC_DOMAIN})
        return records
```

## Concrete deliverable pointer

Maps to plan 2026-07-17 deliverable 6 (H10). Success criterion: NARA
+ Prelinger together contribute ≥ 4 additional `PUBLIC_DOMAIN`
records on the seed query fixtures.

## Falsifier

If, after landing the two adapters, the compare report shows the
new sources contributing 0 records (parsing bug) or contributing
records with `License.UNKNOWN` (default-license bug), the
implementation is wrong. The tests must assert both count > 0 and
license == PUBLIC_DOMAIN on the fixture record we hand-picked
(`A Step-Saving Kitchen`, NARA `naId=1783`).
