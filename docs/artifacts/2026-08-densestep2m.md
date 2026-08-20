# DenseStep2M — dense procedural annotation of HowTo100M

- Paper: *DenseStep2M: A Scalable, Training-Free Pipeline for Dense
  Instructional Video Annotation* (arXiv 2604.26565, April 2026).
- Read: https://arxiv.org/html/2604.26565v1 (accessed 2026-08-20).

## What it does

Given the noisy HowTo100M corpus (1.22M YouTube instructional videos,
23k activities, cooking-heavy), DenseStep2M runs a **three-stage,
training-free** pipeline that emits ~2M temporally grounded procedural
step annotations:

1. **Segmentation** — split each video into ~50s coherent shots
   (Qwen2.5-72B; ASR + shot-cut heuristics).
2. **Step generation** — Qwen2.5-VL-72B samples up to 80 frames/shot at
   1 FPS and drafts candidate step captions grounded to timestamps.
3. **Refinement + verification** — DeepSeek-R1 merges and rewrites the
   candidate steps; Qwen2.5-VL-7B verifies visual↔text agreement and
   keeps only videos where ≥75% of duration is aligned.

Output is a JSONL of `(video_id, [(t_start, t_end, step_text)])` rows.

## Why it matters for us

The **structure** is exactly what a cooking world model wants:
temporally grounded procedural steps with irreversible state changes.
The problem is the **source**: HowTo100M is derived from YouTube videos
without a permissive license, so we cannot ingest their pipeline output
directly, and we cannot rerun the same pipeline on generic YouTube.

## Ideas we should steal (with landing sites)

1. **Three-stage segmentation → generation → verification** is a good
   default architecture for us once we start producing dense
   annotations. Landing site: a future
   `src/specint/annotate/` package. Today: bake the *interface* into
   `VideoRecord.recipe_steps` so we can carry step-level annotations
   even when we harvested them ourselves.
2. **≥75% aligned duration** as a keep/drop filter is a nice, defensible
   quality gate. Landing site: `quality/metrics.py` — add an
   `alignment_ratio` field for future annotations.
3. **Wikihow taxonomy as seed activities** — 23k physical, visual
   activities, filtered to physical verbs. We can port their public
   category tree to our `SourceQuery.terms` seed lists. Landing site:
   `sources/seeds/wikihow_activities.txt` (future).
4. **Per-shot frame budget of 80 @ 1 FPS** — a good conservative default
   for our own future frame extractor.

## Ideas we should refuse

- Re-hosting HowTo100M video content. We can cite results, but any
  training on HowTo100M content violates YouTube ToS and re-hosts
  copyrighted work. Our pipeline never downloads YouTube video bytes.
- Treating YouTube ASR captions as ground truth. DenseStep2M explicitly
  finds that ASR-only supervision is noisy — our text-density metric
  already downweights ASR-heavy descriptions correctly.

## Follow-ups for `plan-YYYY-MM-DD.md`

- Adopt the WikiHow physical-verb seed list as our default cross-source
  query bank (permissively licensed CC-BY-SA at wikihow.com).
- Prototype an `alignment_ratio` heuristic that can be computed
  *without* running a VLM (e.g. length(recipe_steps) × mean(step_len) vs.
  `duration_s` — a proxy, but a defensible baseline in `compare/`).
