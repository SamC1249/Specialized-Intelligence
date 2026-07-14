# DenseStep2M — training-free dense step annotation

- **Paper**: DenseStep2M: A Scalable, Training-Free Pipeline for Dense
  Instructional Video Annotation. arXiv:2604.26565 (2026).
- **Scale**: 1,885,504 dense temporally grounded instructional steps
  over 99,248 videos (~7,212 hours) — extracted **without any
  human labels** by combining a VLM (Qwen2.5-VL-72B) with a reasoning
  LLM (DeepSeek-R1-671B) over noisy HowTo100M videos.
- **Notable metrics**: 19.0 steps/video (vs 10.6 in HowToStep); 46.25
  R1-mIoU on timestamp alignment vs 21.3 baseline.
- **License**: dataset released via Hugging Face; MIT-style pipeline
  code. Source videos remain YouTube (HowTo100M) — **not directly
  redistributable**; the *annotations* are the artifact.

## Why it matters

Two things:

1. **You can synthesize step-level supervision at scale without
   humans.** A VLM+LLM cascade on ASR + sparse frame samples produces
   temporally-grounded steps whose alignment scores rival human labels.
2. **Metadata-only ranking is a strict subset of what's possible.**
   Once we're willing to sample a *few frames*, we jump from title/desc
   heuristics to real procedural density estimates. Our roadmap must
   distinguish (a) URL/metadata triage from (b) frame-sample scoring.

## Concrete hooks into this repo

1. Add a **`quality/frame_sample_filter.py`** module in a future PR (not
   today — needs GPU budget). Contract: given a `VideoRecord` and up to
   N sampled frames (or an ASR transcript), return an updated record
   with `n_steps_estimated: int`. Metadata-only mean is the fallback.
2. Add a **compare mode dimension**: `stage ∈ {metadata_only,
   frame_sampled}` on `BenchmarkResult`, so we can show that
   frame-sampled filters materially move the Pareto frontier without
   losing our current baseline.
3. Add a **HowTo100M provenance note**: HowTo100M itself carries
   YouTube provenance — under our rules we cannot mirror the videos;
   we can only harvest annotations tied to `youtube.com/watch?v=…`
   URLs when the video is CC-licensed (`videoLicense=creativeCommon`).
   Coding-Agent must gate on the intersection.
