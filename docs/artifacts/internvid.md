# Paper note: InternVid (Wang et al., 2023)

- **Paper**: *InternVid: A Large-scale Video-Text Dataset for Multimodal
  Understanding and Generation* — Wang et al. arXiv:2307.06942.
- **Headline numbers**: 7M videos, 760k hours, 234M clips, 16 scenarios,
  ~6,000 motion descriptions.

## What it teaches us

1. **Multiscale captioning.** Coarse: caption the middle frame
   (BLIP-2). Fine: per-frame Tag2Text → LLM-summary into a clip
   caption. Different scales help different downstream tasks.
   *Caveat:* Panda-70M reports the LLM-summary step propagates errors;
   InternVid's results suggest it can still be useful with the right
   prompts. We treat this as a tunable knob, not a fixed recipe.
2. **PySceneDetect + duration cap (~10s).** Concrete pipeline:
   - filter to videos with usable resolution
   - PySceneDetect with a fixed threshold
   - cap clip length around 10s
3. **ICL-style interleaved data (7.1M pairs).** Useful for downstream
   in-context learning; tells us that *interleaving* clips with
   captions is a worthwhile output format alongside flat clip-caption
   pairs.

## What we *cannot* take from it

- The video acquisition is YouTube-based and shares the *Chmura* risk.

## Ideas to implement

- **Multiscale captioning as a `components/captioners/multiscale.py`**
  module that exposes `caption(clip, scale="coarse" | "fine") -> str`.
  Gate the `fine` scale behind a config flag (it is much more expensive
  per-clip).
- **Two output schemas, one shared manifest.** One default
  flat clip-caption manifest; an opt-in interleaved manifest produced
  by a transform layer over the flat one. No new schema in
  `db_structured.md` until we actually need to ship interleaved data
  to a downstream consumer.
