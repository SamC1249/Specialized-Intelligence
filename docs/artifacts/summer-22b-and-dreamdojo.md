# Paper notes: Summer-22B (2026) and DreamDojo (NVIDIA, 2026)

Two papers from the 2026 frontier that together pin down our reference
architecture for *both* the data side (Summer-22B) and the eventual
consumer side (DreamDojo as the canonical world-model).

---

## Summer-22B: A Systematic Approach to Dataset Engineering and Training at Scale for Video Foundation Model

- **Paper**: *Summer-22B: A Systematic Approach to Dataset Engineering and
  Training at Scale for Video Foundation Model.* arXiv:2603.00173 (2026).
- **Headline numbers**: 22B-parameter video foundation model trained on
  ~50M clips. The paper's most useful contribution to *us* is its
  data-engineering methodology, not the model itself.

### What it teaches us

1. **Dataset engineering consumed the majority of the effort.** This is
   a frontier-lab admission, in 2026, that the data flywheel is the
   bottleneck — not architecture. This validates the strategic premise
   of this entire repository.
2. **Reference filter pipeline (multi-stage, in this order)**:
   - Shot boundary detection (TransNet)
   - Aesthetic / quality filtering (DOVER)
   - Color filter (drop monochrome / over-saturated)
   - Thumbnail-collage filter (drop "screensaver" / slideshow content)
   - Optical-flow motion filter (drop static or super-shaky)
   - Foreground/background filter (drop "talking head with no scene")
3. **Filters compose multiplicatively.** Each filter targets a specific
   failure mode, and the paper shows monotonic improvement on
   downstream model loss as filters are added.
4. **Lavender Data system** — they built bespoke tooling for dataset
   management. We will not build a system that big yet, but the design
   pattern of "manifest-driven, filter-as-a-stage" is portable.

### Engineering decisions we adopt today

- **Filter ordering**: shot detection → exclude → score (DOVER, motion,
  optical flow) → score-threshold filter → dedup. Shot detection first
  because everything downstream is per-clip.
- **Per-filter exclusion records**: every filter writes its decision and
  reason into the clip row, *not* a separate file. Reproducible and
  auditable.

---

## DreamDojo: A Generalist Robot World Model from Large-Scale Human Videos

- **Paper**: Gao et al. ICML 2026. arXiv:2602.06949.
- **Headline numbers**: 44k hours of egocentric human video; 2B and 14B
  checkpoint sizes; ~10 FPS real-time autoregressive rollout for >1
  minute after distillation.

### What it teaches us

1. **Scale of egocentric data is now the differentiator.** 44k hours
   beats every prior egocentric corpus. The implication for cooking
   specifically: egocentric kitchen video is the highest-leverage data
   in our domain.
2. **Distillation lets you trade pretrain compute for inference
   compute.** We don't directly pretrain models, but for any captioner
   we ship, we should plan a distill step (Panda-70M does the same).
3. **Action-conditioning matters.** Their model is interactive, not
   passive. **For our data side, this means we should be capturing or
   inferring *action signals*** alongside the video — gripper-state,
   cursor, hand-keypoint, language-of-instruction — so that downstream
   WAM-style consumers can plug in.

### Adversarial concerns this surfaces

- **Egocentric license-clean cooking video is rare.** EPIC-KITCHENS,
  HD-EPIC, and Ego4D are research-license-only. We don't have a clean
  egocentric set. *Action item:* explore an opt-in cooking community
  collection on a federated platform (PeerTube) as a longer-term play
  — see `docs/research/cooking-video-flywheel.md`.
- **Action signal extraction is non-trivial.** From third-person
  cooking video, we can infer hand-keypoints (MediaPipe / RTM-Hand)
  and tool-presence (open-vocab detector); from egocentric video, we
  add head-pose and gaze (where available). This adds an
  `action_signal` extension to our schema in v1, *not* v0.

### Engineering decisions we adopt today

- We *plan* an `action_signal.jsonl` companion manifest for v1 (not in
  `db_structured.md` v0; tracked as an open question).
- We treat egocentric coverage as a strategic gap and write it down in
  `docs/plan/2026-06-20.md` §7.

---

## Combined "frontier reference architecture" for our data flywheel

```
                ┌───────────────┐
discover  ────► │ raw_video.jsonl│
                └────┬──────────┘
                     │ license_check (drop UNKNOWN)
                     ▼
                ┌───────────────┐
                │ raw_video' .jsonl│
                └────┬──────────┘
                     │ TransNet-v2 / PySceneDetect
                     ▼
                ┌───────────────┐
                │ clip.jsonl    │
                └────┬──────────┘
                     │ multi-teacher caption (BLIP-2, VQA) + ASR
                     │ DOVER aesthetic + optical-flow motion + pHash
                     │ open-vocab tool/hand presence
                     ▼
                ┌───────────────┐
                │ clip+features │
                └────┬──────────┘
                     │ pHash bucket → embedding-confirm dedup
                     │ learned WAM-utility filter (planned)
                     ▼
                ┌───────────────┐
                │ shard.jsonl   │
                └───────────────┘
```

Summer-22B gives us the filter recipe; DreamDojo gives us the *target* of
the optimization (egocentric / action-conditioned, not pretty-picture);
HowTo100M / InternVid / Panda-70M give us the multi-teacher captioning and
ontology pieces.
