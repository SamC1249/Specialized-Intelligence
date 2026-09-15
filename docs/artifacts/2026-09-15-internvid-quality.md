# internvid-quality — the industry-standard video quality funnel

Source: [arXiv:2307.06942](https://arxiv.org/abs/2307.06942) (InternVid,
OpenGVLab, 2023; still the reference cascade cited by most video-data
papers as of 2026). Dataset itself is not redistributable — it consists
of YouTube URLs plus derived metadata. What is useful to us is *the
filter cascade*.

## The four-stage filter, verbatim from the paper

1. **Shot segmentation** — PySceneDetect `ContentDetector` with
   `threshold=27`. Clips < 2 s are dropped. Cuts still frames and
   frenetic mashups.
2. **Aesthetic scoring** — LAION open-source aesthetic predictor, sample
   4 frames uniformly, take the **maximum** score across the 4. The
   released `InternVid-Aesthetics-18M` subset applies a threshold of
   `>= 4`.
3. **Caption alignment** — UMT (a video-language model) cosine
   similarity between (4-frame video embedding, caption embedding).
   `InternVid-FLT` keeps clips with the highest UMT-SIM.
4. **Diversity sampling** — `InternVid-DIV` maximises content diversity;
   details are not published as a formula.

Reported distributions (relevant for calibration):
- 85% of clips are 0–10 s after step 1.
- 75% of clips score aesthetic ∈ [4, 6].
- 80% of clips score UMT-SIM ∈ [0.3, 0.4].

## Why we can't just copy this

Steps 1–3 all require *watching the video*. Our current pipeline is
strictly metadata-only, by design, so that we can rank a backlog of
millions of URLs before deciding which few thousand to actually
download.

## Metadata-only surrogates we can ship *today*

| InternVid filter                | Legal metadata-only surrogate |
| ------------------------------- | ----------------------------- |
| PySceneDetect shot count        | `duration_s / len(recipe_steps)` when `recipe_steps` is present. Low ratio ⇒ many state-changes per minute ⇒ dense procedural signal. Falls back to `duration_s` bucket. |
| Aesthetic ≥ 4                   | Weak: presence of `width * height ≥ 720p` AND non-empty description AND author has ≥ 1 prior upload (author-track). |
| UMT-SIM ≥ 0.3                   | Weak: text-density signal we already have, plus a title-language ↔ description-language match (both English, both French, etc.). |
| Diversity sampling              | Cross-source dedup key (see plan H8) + `unique_authors` (already in `BenchmarkResult`). |

None of these surrogates *replace* the real filters. They are triage:
"which URLs deserve the frame-level filter budget?"

## How we'd use it here

- **`src/specint/quality/procedural_density.py`** (new, Coding-Agent PR):
  the `seconds-per-step` component of H10 in `docs/plan-2026-09-15.md`.
  Weight it modestly (~0.10) and validate against the fixture baseline.
- **`src/specint/quality/metrics.py`** — add `WEIGHTS["author_track"] =
  0.05`; requires the harness to know how many records share an author
  across a run. Small refactor.
- **`docs/plan-*.md`** — document that our scorer is an *upstream
  triage* signal, not a substitute for InternVid-style frame-level
  filtering. Any future frame-level step must live in a separate module
  gated by a new `--allow-frame-download` flag.

## Trap to avoid

InternVid is *YouTube-seeded*. Its numbers are not directly comparable
to ours because the underlying distribution is different. When our
comparison harness beats their aesthetic distribution, it does not mean
our data is better — it means our data is different. Log the raw
histograms, not just the means.
