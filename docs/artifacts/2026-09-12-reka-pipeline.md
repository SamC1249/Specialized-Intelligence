# Reka Labs — World-Model Data Pipeline

**Citation.** "World Model Data Pipeline", Reka Labs, 2026.
<https://reka.ai/vision/news/world-model-data-pipeline>.

## One-line summary

Production pipeline for the Reka "omni" world model: petabyte-scale
ingestion → 9-model quality bank → embedding-based dedup →
standardized delivery to training clusters, run continuously.

## Why this matters for us

Reka's post is the clearest public description of an industrial
video-world-model data pipeline. It confirms which stages actually
matter for downstream model quality — and, critically, in which order
they must be sequenced so that expensive stages only run on candidates
that survive cheaper ones.

Confirms our design intuition:

- Metadata-only cheap-first cascade before frame-level scoring.
- Deduplication is done on *embeddings*, not raw pixels, and is the
  single largest quality lever.
- Delivery is in staged increments so training can start on early
  batches — the same shape our `reports/` versioning supports.

## What to steal

1. **The "analyze a little bit first" heuristic.** Reka explicitly
   describes running only a tiny analysis before deciding to keep a
   video for full analysis. Our version: `quality/metrics.py` should
   short-circuit as soon as license is `RESTRICTED` — we should never
   compute duration/resolution scoring on a record we cannot use.
   (Cheap; ship in a follow-up PR.)
2. **9+ quality analysis models.** Concrete stages worth
   *scheduling* (even before we have models): aesthetic, text overlay
   (OCR density), NSFW gate, motion, audio-presence, black-frame
   fraction, camera-shake, subtitles-alignment, and OCR-cleanliness.
   Track each as a nullable `float` on `VideoRecord`; adapters that
   don't produce them leave `None`, which the scorer treats as
   "unknown" (weight neutral).
3. **Embedding-based dedup.** Reka states embeddings are computed
   during the same stage as the quality bank, so dedup is essentially
   free. Once we can afford *any* frame analysis, dedup should ride on
   its output — do not build a bespoke dedup encoder later.
4. **Staged delivery.** Reka delivers in increments; the research team
   trains on the early ones. Our analog: our nightly `reports/`
   compare-JSON *is* the increment. We should date-stamp every report
   and never overwrite yesterday's.

## What to not steal

- Their assumption of a captive multi-thousand-GPU cluster. Any stage
  we adopt must be runnable in CPU-only CI (offline fixtures) even if
  the production version needs GPUs.

## Follow-ups filed

- Add optional per-clip quality slots (`aesthetic`, `motion`,
  `nsfw_score`, …) to `VideoRecord` in a schema PR before we ship any
  frame-level scorer. Not done in this iteration; do not front-load
  the schema until we can produce at least one such value legally.
- Short-circuit `score_record` on `License.RESTRICTED`. Low-risk;
  candidate for the next Coding-Agent PR.
