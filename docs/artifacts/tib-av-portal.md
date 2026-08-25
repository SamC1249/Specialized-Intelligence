# TIB AV Portal — scientific video with CC0 metadata

- **Portal:** <https://av.tib.eu/>
- **Open data page:** <https://av.tib.eu/opendata>
- **OAI-PMH endpoint:** <https://www.tib.eu/mdg/oai>
  (set: `kmo-av`; formats: OAI DC, MARC XML, RDF XML, JSON-LD,
  Turtle, N3)
- **Reference:** *The TIB AV Portal: Unlocking Discovery and
  Interoperability of Scientific Videos*, Plank 2023.
  <https://doi.org/10.5281/zenodo.8087227>

## What it is

The German National Library of Science and Technology publishes
~40,000 quality-checked scientific videos — lectures, conference
recordings, simulations, experiments, video abstracts — predominantly
under Creative Commons licences. The **metadata and thumbnails** are
released under **CC0 1.0** as bulk JSON-Lines / RDF-Turtle dumps and
via OAI-PMH; the underlying videos carry per-item CC licences (mostly
CC-BY / CC-BY-SA / CC-BY-NC-SA — we exclude NC per our license enum).

## Why it matters for Specialized-Intelligence

AGENTS.md's mission is broader than cooking: "surgery, lab work,
sports, manufacturing, etc." TIB AV Portal is the single cleanest
open source for **lab experiments and instructional science video**.
Adding it now:

- Pressure-tests our claim that the pipeline generalises beyond
  cooking — the first non-cooking source in the allowlist.
- Demonstrates the "provenance-first" pattern at its cleanest: CC0
  metadata means we can commit *actual TIB records* as CI fixtures
  without any redistribution risk.
- Proves the harness handles a source whose primary API is OAI-PMH
  XML, not JSON — a useful stress test for `BaseSource`.

## Concrete implementation ideas

- Add `src/specint/sources/tib_av_portal.py`.
- `parse(raw)` consumes an OAI-PMH `ListRecords` XML tree via `lxml`;
  emit a `VideoRecord` per `<record>` whose `<licence>` matches
  `{CC-BY, CC-BY-SA, CC0, PD}`.
- `search(query)` walks pages with `resumptionToken`. Rate-limit to
  1 QPS (they do not publish a QPS policy; be polite).
- Fixture: 3–5 real records from the CC0 dump, checked into
  `tests/fixtures/tib_av_portal/`.
- Add a `n_science` counter to `BenchmarkResult` (via `notes`) so we
  can slice cooking vs. non-cooking yield without changing the schema
  yet.
- Comparison-first: baseline against Internet Archive on a "physics
  experiment" `SourceQuery`. Hypothesis: TIB dominates on
  `mean_quality` and `n_license_clean`, IA dominates on `n_records`.
