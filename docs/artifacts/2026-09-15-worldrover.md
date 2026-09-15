# worldrover — synthetic Unreal Engine data engine for world-model pretraining

Source: [arXiv:2608.15659](https://arxiv.org/abs/2608.15659) (Xu, Lin,
Li, Liu, Zhang, Ge — 2026), preview dataset released under the license
declared at
[huggingface.co/datasets/xjxu21/WorldRover](https://huggingface.co/datasets/xjxu21/WorldRover).
The preview covers ~4.1 hours; the paper claims a `10M`-frame /
`202.7`-hour internal corpus that is not yet public.

## What the paper does

Builds a headless Unreal Engine pipeline that ingests artist-made asset
packs (30+ scenes), plans routes, and *replays the same route* under
three cameras (first-person, third-person, 360° panoramic) and multiple
lighting / material styles. Emits paired RGB, metric depth, dense
optical flow, long-range 2D/3D point tracks, camera trajectories,
character trajectories, and derived action streams. The core
architectural claim is that "the missing capability is not more rendered
frames but a production system that scales variation while preserving
the factors shared across related observations."

A companion paper ([arXiv:2609.03557](https://arxiv.org/abs/2609.03557),
"Building Pretraining Data for World Models…") describes an even larger
UE cluster (25 servers × 8× RTX 5090) that emitted 2,691 hours of 1080p
and 6,076 hours of 720p under a similar architecture. Both papers gate
raw output through *automated scene screening, aesthetic and luminance
filtering, partial-output recovery, and continuous cluster health
monitoring*.

## Why this is relevant to Specialized-Intelligence

Synthetic UE data cleanly solves two of our hard problems by
construction:

1. **Provenance is trivial** — every frame carries pose, action, and
   render-time metadata. AGENTS.md hard-constraint #2 is a compile-time
   check, not a runtime hope.
2. **License is trivial** — the licensor is us. `License.CC0` or
   `License.OTHER_FREE`, no HTTP round-trips.

It also loses two things that make real video valuable:

1. **Distribution shift** — no synthetic engine yet captures the greasy,
   partially-lit, occluded texture of a real home kitchen. See EchoWM's
   own limitations discussion.
2. **Task-language alignment** — the "recipe" of a scripted UE camera
   walk is trivial; the "recipe" of a real cooking video is exactly the
   procedural supervision we care about.

## How we'd use it here

Do **not** attempt to reproduce a UE cluster in this repo. Instead:

- Treat WorldRover-preview (`~4.1 h`) as an out-of-band evaluation
  distribution: a `tests/fixtures/worldrover_manifest.json` (metadata
  only, no frames) sanity-checks that our downstream world-model
  consumer can ingest a *known-good* format. Files to touch (later
  Coding-Agent PR):

  - `src/specint/sources/worldrover.py` — new adapter that reads the
    HuggingFace-hosted metadata manifest (no live download) and emits
    `VideoRecord` rows with `License.CC0` or matching declared license.
  - `tests/fixtures/worldrover/preview_manifest.json` — a small offline
    slice of the manifest.
  - `src/specint/compare/harness.py` — no change; the harness must
    accept a synthetic source without special-casing.

- Add "synthetic vs. real" as a benchmark axis. New `BenchmarkResult`
  columns `is_synthetic: bool` and `has_ground_truth_actions: bool`
  would let a downstream mixer pick a real:synthetic ratio.

- **Do not** classify synthetic frames as substitutes for procedural
  cooking footage. WorldRover's own paper reports no downstream results;
  including it in the training-corpus mix without an ablation would be
  cargo-culting.

## Open questions

- Is there a synthetic-cooking-scene UE asset pack? A quick search of
  the UE Marketplace suggests yes (a few "kitchen sim" packs), but
  their licenses would need per-asset review.
- Does WorldRover's action stream align with anything we can query in
  the metadata-only mode we currently operate in? Probably not — the
  action stream lives inside the tarball, not the manifest.
