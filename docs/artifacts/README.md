# docs/artifacts — research notes

Each file here summarises one paper, dataset, or upstream system and
records **how we would implement it** or **what it teaches us** about
our own pipeline. Keep entries short: the point is to convert reading
into concrete follow-ups in the next `docs/plan-YYYY-MM-DD.md`, not to
mirror the paper.

Every note has three sections:

1. **What it is** — one paragraph.
2. **Why it matters for Specialized-Intelligence** — how it maps to
   AGENTS.md constraints (legality, provenance, yield, quality).
3. **Concrete implementation ideas** — bullet-list. Each bullet
   becomes a candidate deliverable for a future plan.

## Index (2026-08-25)

- `web-data-commons.md` — WDC schema.org corpora derived from Common
  Crawl. Direct replacement for our stub `common_crawl` adapter.
- `tib-av-portal.md` — CC0-metadata, CC-BY/CC-BY-SA scientific videos
  with an OAI-PMH interface. Legit allowlist addition for adjacent
  "difficult video" domains (lab work, experiments).
- `finevideo-and-youtube-commons.md` — Hugging Face's FineVideo + the
  YouTube-Commons project (CC-BY YouTube aggregation). Reference model
  for our own YouTube CC harvester.
- `openvid-and-videoufo.md` — CC-BY-4.0 packaged corpora. Benchmark
  *targets* to prove yield, not sources to re-scrape.
- `mlt-dedup-and-videohash.md` — near-duplicate video detection. Phase
  plan for `specint.dedup`.
- `captaincook4d-promqa-qualcomm.md` — procedural cooking benchmarks
  we want our data to be useful for.
- `videoauteur-long-narrative.md` — ICCV'25 long-form cooking dataset;
  validates the "long-horizon procedural" thesis and the
  W4 duration-curve fix.
