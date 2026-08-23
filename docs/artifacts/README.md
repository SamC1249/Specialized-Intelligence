# docs/artifacts/

Curated notes on external research relevant to the mission (legally-sourced,
internet-scale video data for frontier world models). One file per paper,
standard, or dataset, with:

1. Bibliographic citation and permalink.
2. What the artifact claims, in one paragraph.
3. What is directly transferable to `specint` (concrete implementation
   hooks with file paths).
4. What is *not* transferable (licence, scope, missing infra).
5. Adversarial notes — the load-bearing assumption we should attack next.

Notes are written by `Adversarial-Agent` and consumed by `Coding-Agent` and
`Reviewer-Agent`. Every plan under `docs/plan-YYYY-MM-DD.md` should cite the
artifacts it draws on so future readers can retrace the reasoning chain.

## Index

- `2026-ego2world.md` — HD-EPIC → executable graph-transition world model
  benchmark (arXiv 2605.13335).
- `2026-densestep2m.md` — training-free VLM pipeline for dense procedural
  step annotation of instructional video (arXiv 2604.26565).
- `2026-mlt-dedup.md` — multi-level, spatial-temporal near-duplicate video
  detection (KDD 2026).
- `2026-streaming-world-model.md` — physical-prior distillation via 120K
  real-world physical-interaction clips (arXiv 2608.07981).
- `2026-eu-ai-act-transparency.md` — Art. 53(1)(d) training-data
  transparency template obligations for GPAI providers.
- `2026-tdmrep-and-aipref.md` — TDMRep, IETF AIPREF, IPTC opt-out signals,
  and how a lawful crawler must honour them.
- `2026-peertube-sepiasearch.md` — federated PeerTube search via the
  SepiaSearch API.
