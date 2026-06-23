# Paper note: Panda-70M (Chen et al., 2024)

- **Paper**: *Panda-70M: Captioning 70M Videos with Multiple
  Cross-Modality Teachers* — Chen, Chao, Jeon, Fang, Lee, Tulyakov.
  CVPR 2024. arXiv:2402.19479.
- **Construction**: Started from 3.8M "long" videos drawn from
  HD-VILA-100M's YouTube ID list, split into 70.8M semantically
  coherent clips, captioned by an ensemble of cross-modality teachers,
  finalized by a fine-tuned retrieval model that picks the best caption.

## What it teaches us

1. **Semantics-aware splitting beats fixed-window or single-threshold
   shot detection.** They balance scene coherence vs. clip duration in
   one optimization, rather than just thresholding PySceneDetect.
2. **Multi-teacher captioning beats any single VLM.** They fan out an
   image captioner, image-VQA, and video-VQA in parallel, then pick
   among them. **Critically, they noted that letting an LLM "summarize"
   teacher outputs propagates errors** — a retrieval-pick is more
   robust. We should adopt the retrieval-pick pattern, not the
   LLM-summary pattern.
3. **Distillation of the captioning ensemble** into a single
   two-branch student model is what makes 70M-scale captioning
   tractable. Worth replicating once we have a small in-house gold
   set.
4. **Desirability filtering and shot boundary detection** were *added
   later (Oct 2024)*. The lesson: we ship a v0 without these and
   bolt them on without re-architecting.

## What we *cannot* take from it

- **The video bytes.** Panda-70M is the dataset cited in *Chmura v.
  Snap* as the problematic artifact. The 36 TB tarball is sourced
  from YouTube via HD-VILA-100M, which is the live-litigation source.
- **The HD-VILA-100M ID list as an acquisition seed.** Same reason.

## Ideas to implement (license-clean adaptation)

- **Multi-teacher captioning as a generic, source-agnostic component.**
  In `components/captioners/`, wrap N caption teachers behind a single
  `Captioner` interface; have a `RetrievalSelectorCaptioner` that takes
  a list of `Captioner`s and a small video-text retrieval model and
  emits the best caption. This is independent of the data source and
  reusable across all our license-clean inputs.
- **Splitter benchmark.** On a held-out license-clean set, compare
  PySceneDetect (v0) and TransNet-v2 (v1) against a small human-labeled
  set with metrics: scene-boundary F1 at IoU 0.5, average clip length,
  rate of "scene split mid-action" failures. Important because cooking
  videos have continuous-action scenes broken by camera cuts; bad
  splitting destroys WAM utility.
