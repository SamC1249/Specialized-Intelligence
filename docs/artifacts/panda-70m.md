# Panda-70M — multi-teacher captioning at 70M-video scale

- Paper: Chen et al., *Panda-70M: Captioning 70M Videos with Multiple
  Cross-Modality Teachers*, CVPR 2024.
- Project / data loader: <https://github.com/snap-research/Panda-70M>
- HTML version: <https://arxiv.org/html/2402.19479>

## What it is

Panda-70M seeds from HD-VILA-100M (YouTube) and processes 3.8 M
long-form videos in three stages:

1. **Semantics-aware splitting** — long videos cut into semantically
   coherent clips (not just shot boundaries).
2. **Multi-teacher captioning** — several image/video VQA models
   (BLIP-2, VideoChat, Video-LLaMA, ...) each propose a caption.
3. **Retrieval-based oracle** — 100 K human-ranked captions train a
   video→text retrieval model that then picks the best teacher caption
   for the remaining 69.9 M clips.

The released 10 M subset keeps only clips whose matching score ≥ 0.43
and at most 3 clips per source video, which is where **the quality
signal actually lives**: Panda-70M is not "70 M high-quality clips", it
is "70 M candidates" with a documented filter.

## Why we care

- Confirms that **candidate-generation and filtering are two different
  problems**. `specint` conflates them today: our `quality_score` is a
  late-stage ranker, but we have no explicit candidate layer.
- Shows a tractable alternative to a single VLM scorer: an *ensemble of
  cheap teachers plus a learned ranker*. This is important for us
  because we cannot rely on YouTube-sourced data under our hard
  constraints — but the same ensemble pattern applies to captioning the
  CC-licensed clips we do collect.
- Their meta-filter "`desirable | still_foreground_image |
  tiny_camera_movement | screen_in_screen | computer_screen_recording`"
  is directly re-usable as a *post-ingest* label set.

## Implementation hook

- `src/specint/quality/metrics.py` — add a `candidate_class` enum
  mirroring the Panda-70M `desirabilityFiltering` label set. Even
  without a VLM, we can heuristically detect `computer_screen_recording`
  (title/description regex: "screencast", "walkthrough", "tutorial"
  without "food"/"recipe"/"kitchen") and
  `tiny_camera_movement` (duration > 1 h with "static" or "tripod" in
  title). Record the predicted class on `VideoRecord` so downstream
  dedup / sampling can bucket on it.
- `src/specint/compare/harness.py` — report per-class counts in the
  benchmark row (`notes` field is already free-form; promote to a
  structured map once a second class ships).
- `src/specint/quality/dedup.py` (shipped today) — the "at most N
  clips per source video" cap in Panda-70M is a dedup policy. Expose a
  `max_per_author` knob with the same intent.

## Risks / disagreements

- Panda-70M downloads YouTube videos. We **do not**: our YouTube path
  is URL+metadata only, and only when `videoLicense=creativeCommon` is
  set. The lesson we take is the *pipeline shape*, not the source.
- Their "best teacher caption" oracle presupposes human annotation.
  We will not have 100 K human-labelled clips. Workaround: start the
  ranker with heuristic positive/negative pairs (CC-BY recipe pages
  with declared `recipeInstructions` as positives, pages with
  JSON-LD-only stock-footage pointers as negatives).
