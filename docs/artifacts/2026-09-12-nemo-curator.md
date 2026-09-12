# NeMo Curator + Data-Juicer — Video Quality Filter Stack

**Citations.**

- NVIDIA NeMo Curator, "Curate Video / Filtering" (2025-06).
  <https://docs.nvidia.com/nemo/curator/curate-video/process-data/filtering>
- Data-Juicer `VideoMotionScoreFilter` (v1.4.5).
  <https://github.com/datajuicer/data-juicer/blob/v1.4.5/data_juicer/ops/filter/video_motion_score_filter.py>
- PySceneDetect 0.7 detectors
  (<https://www.scenedetect.com/docs/latest/api/detectors.html>): content,
  adaptive, threshold, hash-based (DCT), histogram (YUV).
- DOVER: disentangled aesthetic/technical video quality evaluator.

## One-line summary

The current open-source consensus stack for pruning generative-model
training video is: scene split (PySceneDetect) → motion score
(OpenCV Farneback in Data-Juicer, or lightweight decoded motion vectors
in NeMo Curator) → aesthetic score (CLIP-based) → OCR density → NSFW.
Filters are ordered cheap-to-expensive; each dropped clip is recorded
with the stage that dropped it.

## Why this matters for us

Our `quality/metrics.py` scores metadata only, and its highest-weighted
component is `license_clean`. That's correct for a corpus decision but
useless for ranking two license-clean 1080p CC-BY cooking clips against
each other. Every downstream filter here is model-training-relevant and
gives us a knob the metadata layer cannot.

None of these tools requires GPU for *unit testing*: PySceneDetect and
Data-Juicer's OpenCV path run on CPU; NeMo Curator's aesthetic stage is
CLIP-based but we can shim it out with a fixed-return stub during
tests.

## What to steal

1. **Stage-tagged filtering.** Every dropped clip carries a
   `filtered_by ∈ {motion, aesthetic, ocr, nsfw, license, duration,
   duplicate}`. We already track dedup rejects (`2026-09-12-video-
   dedup.md`); the same shape scales to N stages.
2. **Motion score via Farneback optical flow.** Data-Juicer's
   `VideoMotionScoreFilter` (v1.4.5) is 200 LOC of pure OpenCV. Ship it
   as `specint.quality.motion` behind an optional `[frames]` extra.
3. **Scene split via PySceneDetect `AdaptiveDetector`.** Deterministic,
   pure-CPU, fixture-testable if we ship a 5-second sample video (must
   be a CC-BY sample from Blender's official CC-BY corpus or Wikimedia
   Commons, ≤512 KB per the pre-commit rule).
4. **Aesthetic score with a *stub* interface.** We do not want a CLIP
   dependency in CI. Ship an `AestheticScorer` protocol with a
   deterministic `RandomAestheticScorer` implementation for tests; real
   CLIP-based scorer lives behind an optional extra and never runs in
   CI.
5. **DOVER-style dual score (aesthetic + technical).** The community
   has converged on decoupling "does it look pretty" from "is it
   focused, well-encoded, not black-frames". Model this in the schema
   as `quality_aesthetic: float | None`, `quality_technical: float |
   None` — the aggregator picks either mean or min per config.

## What to not steal

- **NeMo Curator's Ray-based scheduler.** Overkill until we have >1
  GPU node.
- **Any filter that requires downloading a video to compute a
  metadata-tier answer.** Motion and aesthetic scores are frame-tier
  and must not run before dedup + license filters.

## Follow-ups filed

- Motion / aesthetic implementations live behind an optional extra;
  wiring can land after we have a legally sourced fixture video ≤512
  KB. Not this iteration.
- Extend the compare report so an aggregate "candidates surviving each
  stage" funnel becomes plottable. That is a real graph the training
  team can act on.
