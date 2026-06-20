# Paper note: V3C — and the case for license-clean video collections

- **Paper**: *V3C — a Research Video Collection.* Rossetto et al.
  arXiv:1810.04401.
- **Headline numbers**: ~3,800 hours of CC-licensed video sourced from
  Vimeo, partitioned into V3C1/V3C2/V3C3 of increasing complexity.

## Why this paper matters disproportionately to us

V3C is the canonical example of a *license-clean* internet video
collection built explicitly because YouTube was not viable. From the
paper:

> "Vimeo was chosen over YouTube because while YouTube offers its users
> the possibility to publish videos under a creative commons attribution
> license which would allow the reuse and redistribution of the video
> material, **YouTube's Terms of Service explicitly forbid the download
> of any video on the platform** for any reason other than playback in
> the context of a video stream."

That single sentence is, in 2026, the legal-architectural justification
for our entire substitute graph (`docs/plan/2026-06-20.md` §3 and
`docs/artifacts/legal-landscape.md`).

## What it teaches us about pipeline design

1. **Per-video master segments by shot boundary** are a useful
   intermediate (V3C calls them "key-frame indexed segments"). This
   matches the modern Summer-22B / Panda-70M recipe.
2. **Multiple resolution outputs in the manifest**: V3C provides both
   full-resolution key-frames and a 200-px-tall thumbnail for fast
   browsing. We should follow suit and store thumbnail derivatives in
   shard manifests for downstream debug UIs.
3. **Three partitions of increasing complexity** is a clean way to
   structure a benchmark; we copy this for our `purpose: probe |
   eval | held_out` distinction in `db_structured.md` §2.3.

## Limits and what we add on top

- V3C is general-purpose, not cooking. Our value-add is a vertical
  cooking layer + license-clean methodology that is platform-neutral
  (Vimeo *plus* Wikimedia, Internet Archive, PeerTube, government
  open archives).
- V3C does not maintain a takedown SLA in the paper. We make this
  explicit in our shard manifests.

## License-clean source matrix (engineering checklist)

For each candidate source, we need a per-source adapter that emits:

- a stable canonical URL (the *page* URL, not the media URL — a media
  URL can rotate; a page URL is what a takedown notice references)
- an SPDX-style license string + a confidence in [0, 1]
- the attribution string the license requires
- a callable to verify the license at retrieval time (re-check before
  every batch)

This adapter contract belongs in `components/sources/<source>.py`. To be
implemented in subsequent sessions; see `db_structured.md` §3.
