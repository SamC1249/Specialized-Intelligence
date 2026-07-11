# World-model quality filters we should port

_Adversarial-Agent, 2026-07-11_

## Question

Our current `quality/metrics.py` is a five-component metadata-only
score. Where does it fall short of what's already published for
world-model / action-grounding pretraining, and which filters are
achievable *without downloading media*?

## Filters from recent literature

### 1. Observability filtering (WorldPrediction, 2025)

WorldPrediction filters procedural video by computing DINOv2 feature
distance between the initial and final observation and rejecting pairs
with distance above a threshold (drastic camera / scene changes that
break causal inference). This eliminates video edits, cut-aways, and
severe viewpoint shifts before any downstream training.
Source: <https://arxiv.org/html/2506.04363v1>

**For us (metadata-only proxy):** if a record's declared duration is
under 5 seconds and its title contains "trailer" / "montage" /
"compilation" / "aftermovie", it's almost certainly not a coherent
procedural episode. A blocklist regex applied to `title` +
`description` is a cheap first-pass observability filter.

### 2. Action-centric caption filtering (InstrAction, 2026)

InstrAction refines HowTo100M by:

- Filtering non-instructional ASR captions with an LLM.
- Extracting verb phrases as fine-grained temporal supervision.
- Generating *hard negatives*: verb-altered ("chop" → "grate") and
  order-swapped variants that force the model to attend to motion
  rather than static objects.

Source: <https://arxiv.org/html/2604.08762v1>

**For us:** a lightweight *verb density* signal is achievable now with
no ML. Count the intersection of cooking-action verbs (`chop`, `dice`,
`sauté`, `simmer`, `whisk`, `fold`, ...) in title + description +
`recipe_steps`. Normalize to [0, 1] against a target of ~20 verb
occurrences per record. Domain-swappable: for surgery we would swap
in "suture", "incise", "cauterize"; for lab work we'd add "pipette",
"centrifuge", "titrate".

### 3. Luminance / technical / subtitle filtering (Sekai, 2025)

Sekai's fine-tuning corpus for world-model video generation uses:

- **Luminance filter**: reject clips where >X% of frames are extremely
  dark or bright (measured on the Y channel).
- **Technical quality**: reject the lowest-scoring 10% by COVER (an
  aesthetic + technical video quality model).
- **Subtitle detection**: reject clips with hardcoded burned-in
  subtitles (bad for pixel-space world models).
- **Camera trajectory sanity**: reject clips whose per-frame camera
  motion, estimated via SfM, has >1 abrupt >150° reversal in 10 s.

Source: <https://arxiv.org/pdf/2506.15675>

**For us (deferred):** these all require media. Note them in a
`docs/artifacts/` roadmap; once we start downloading, the first
filter to port is luminance (cheap, catches all-black lead-ins and
mis-encoded files).

### 4. Latent-action pretraining (DreamDojo / LAWM, 2025-2026)

Both propose using continuous latent actions as unified proxy labels
across heterogeneous video (robot demos, egocentric human videos,
web instructional). Directly relevant to our goal of a general
"difficult video" corpus: the *quality-of-motion* signal, not the
*quality-of-language*, ends up mattering most. Encourages the
argument that we should over-collect and let the model do the
labelling — but only if the collected videos are legally clean.
Sources: <https://arxiv.org/html/2602.06949v1>,
<https://arxiv.org/html/2509.18428v1>

## What we ship this iteration

- **New quality component**: `action_density` (domain-aware verb count
  in title+description+recipe_steps). Weight it moderately (0.15) and
  adjust so the total component weights still sum to 1.0.
- **Adversarial filter**: reject titles containing
  {`trailer`, `montage`, `teaser`, `aftermovie`, `compilation`,
  `highlights`} in the CLI-visible score explanation.
- **Domain registry** (`domains.py`) with per-domain verb vocabularies
  and seed terms, so we can run the harness on surgery / lab / sports /
  manufacturing tomorrow without touching the sources.
