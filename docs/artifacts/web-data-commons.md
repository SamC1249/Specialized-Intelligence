# Web Data Commons — schema.org corpora from Common Crawl

- **Primary reference:** Bizer et al., *The Web Data Commons Schema.org
  Table Corpora* (2024). <https://doi.org/10.1145/3589335.3651441>
- **Project page:** <http://webdatacommons.org/>

## What it is

Web Data Commons (WDC) re-processes Common Crawl WARCs with the Any23
parser and publishes structured extractions of every JSON-LD,
Microdata, RDFa, and Microformats block by schema.org class. The 2023
release contains 97 billion RDF quads, and the *class-specific
subsets* (39B quads) let you pull only `VideoObject`, `Recipe`,
`HowTo`, `Article`, etc. Extraction runs on 250 AWS spot instances for
~4,600 machine-hours; **we do not need to redo it.**

## Why it matters for Specialized-Intelligence

Our current `CommonCrawlRecipeSource` only implements `parse` on a
single HTML fixture — `search()` returns `[]`. Reprocessing Common
Crawl WARCs to find schema.org VideoObject/Recipe blocks would cost
thousands of machine-hours; WDC has already done it, publishes the
results under an open license, and updates yearly. This is a
*direct* solution to weakness **W7** in `plan-2026-08-25.md`.

Two important caveats before we trust WDC extracts as training data:

1. **The JSON-LD `contentUrl` frequently lies** (recipe sites embed
   YouTube ARR videos and self-declare CC in the schema block). We
   must ignore the block-level license and require a *host-level*
   permissive license (Wikibooks recipe pages, PD-Cook, etc.). Same
   discipline the seed plan already flagged.
2. **Attribution back to Common Crawl** is required by the WDC license;
   this fits naturally in our `Provenance` model.

## Concrete implementation ideas

- Add `src/specint/sources/wdc_schema.py` that consumes WDC's
  class-specific N-Quads dumps (streamed from
  `https://webdatacommons.org/structureddata/`).
- Parse quads with `rdflib` into `VideoObject` and `Recipe` records,
  join by the `mainEntityOfPage`/subject URI, and only emit
  `VideoRecord`s whose page URL matches a host in a curated
  allowlist file (`data/wdc_permissive_hosts.txt`, versioned).
- Add a `wdc` slug to `REGISTRY`; `parse()` operates on an in-memory
  list of quads (easy fixture: 10–20 quads in a `.nq` file);
  `search()` iterates the remote dump.
- Emit `n_records`, `n_license_clean`, `n_host_denied` counters in
  `BenchmarkResult.notes` for auditability.
- Comparison target: WDC-derived `mean_quality` must ≥ current
  `common_crawl` fixture baseline before we retire the stub.
