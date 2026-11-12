# VidaForge (GAIR-NLP)

- **Repo:** <https://github.com/GAIR-NLP/VidaForge>
- **Licence:** Apache-2.0 (code); dataset outputs inherit the source
  licence of the underlying videos.
- **Pipeline:** 5 stages — ingestion → segmentation → selection →
  annotation → packaging. Dedup uses PDQ (hash) + Cosmos-Embed
  (semantic), running inside the "selection" stage.

## One-line summary

A second, independent open-source confirmation of the Cosmos-Curator
playbook, with a simpler interface and a clearer separation between
*hash-based near-duplicate detection* and *semantic-embedding
duplicate detection*.

## Why it matters to us

- **Cross-check the dedup design.** Two independent frontier labs picked
  the same 2-stage dedup (hash + embedding). We should too. H5 proposes
  a trivially-cheap metadata-only dedup *before* either; VidaForge treats
  metadata dedup as implicit (dropping the same source URL) and runs
  content dedup on the frames. We cannot afford frame dedup in CI; H5's
  metadata dedup is the correct *first* line.
- **PDQ hashes are available in a permissively-licensed Python package
  (`perception`, `pdqhash`).** When we eventually enrich with frames,
  PDQ gives us a frame-level fingerprint without GPU dependency.
- **Scene-cut segmentation (2–10 s clips).** Confirms our world-model
  training unit is *clips*, not whole videos. Our `VideoRecord` currently
  represents a whole video; we will need a `Clip` child when we add
  segmentation. Captured for a future schema migration.

## What we can / can't copy

- **Can:** All of the code is Apache-2.0. We can import the hashing
  helpers directly or vendor the dedup routine.
- **Can't:** No licence restrictions beyond Apache-2.0 attribution.

## Concrete actions

1. When we add `src/specint/dedupe/`, put the metadata-only near-dup
   collapser (H5) in `dedupe/metadata.py`, leave a `dedupe/hash.py`
   stub (future PDQ), and a `dedupe/semantic.py` stub (future
   Cosmos-Embed or SigLIP).
2. Add a note in the next plan tracking "frame-level dedup" as a
   *separate* milestone requiring its own environment (GPU) and
   therefore out of scope for CI.
