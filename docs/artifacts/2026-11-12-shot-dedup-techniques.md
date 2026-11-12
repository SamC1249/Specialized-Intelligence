# Shot segmentation + perceptual-hash dedup (technique notes)

Sources surveyed:

- TransNetV2 (shot boundary detection, soCzech/TransNetV2 + the 2025
  PyTorch port `transnetv2-pytorch`). MIT-licensed. Returns
  `(shot_id, start_time, end_time)` triples.
- PySceneDetect `detect-hash` (pHash on adjacent frames, `imagehash`
  internally).
- `perception` (PyPI) — ships pHash, PDQ, dHash, aHash, Marr-Hildreth,
  wavelet hash, Block Mean, Color Moment; optional FAISS ANN.
- Blog: "Building a Perceptual Hash Pipeline for Video Deduplication in
  Python" — walks through DCT-based 64-bit pHash + BK-tree indexing +
  temporal-fraction matching. Important finding: single-frame hash is
  insufficient because viral content shares intros/stock shots.

## One-line summary

The modern open-source dedup stack is a 3-tier cascade:
*cheap metadata dedup* → *perceptual-hash dedup on representative
frames* → *semantic-embedding dedup across clips*. Each tier is
strictly more expensive than the last.

## Why it matters to us

- H5 lives entirely in tier 1 (metadata). That is correct for CI and
  for triaging 10^9 records. Anything heavier belongs in an
  enrichment pass outside CI.
- When we *do* add tier 2, the right data structure is a BK-tree
  indexed by Hamming distance on 64-bit pHashes, scanning "everything
  within k≈6 bits of this hash" in sub-linear time. Then we require a
  temporal-overlap check (≥70 % of sampled frames must match) before
  collapsing.
- Shot boundaries first. If we dedupe at whole-video granularity we
  lose everything Cosmos/VidaForge gained by clipping to 2–10 s
  segments. The TransNetV2 PyTorch package is a plug-in replacement
  for the TF model and is MIT-licensed; low adoption risk.

## What we can / can't copy

- **Can:** All three libraries (`transnetv2-pytorch` MIT, `perception`
  Apache-2.0, `PySceneDetect` BSD-3). PDQ is Meta's PDQ (BSD-3).
- **Can't:** PDQ is sensitive — Meta ships it for CSAM hashing; our
  use is unrelated (near-dup detection for CC-licensed cooking video),
  but we must not re-publish the PDQ *reference database*.

## Concrete actions

1. Reference this doc from the next Coding-Agent plan item that
   introduces `src/specint/dedupe/hash.py`.
2. Explicitly decide now: **tier 1 ships in CI; tier 2 and tier 3 run
   only behind the `SPECINT_RUN_INTEGRATION=1` flag or a separate
   workflow.** This keeps the "CI must pass offline" invariant.
3. If/when we add TransNetV2 as an optional dep, gate it behind an
   `[extras]` key in `pyproject.toml` so `pip install specint` stays
   lightweight.

## Key snippets we may reuse (documentation only; not committed as code)

```
# DCT-based 64-bit perceptual hash of a BGR frame.
#   img -> 32x32 grayscale -> 2D DCT -> 8x8 low-freq -> median threshold
#   Hamming distance between two hashes approximates perceptual distance.
```

```
# Shot detection:
#   model = TransNetV2(device='auto'); model.load_state_dict(...)
#   scenes = model.detect_scenes("video.mp4", threshold=0.3)
#   -> [{'shot_id': i, 'start_time': s, 'end_time': e}, ...]
```
