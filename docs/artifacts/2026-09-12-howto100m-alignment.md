# HowTo100M and the Speech-Alignment Trap

**Citations.**

- Miech et al., "HowTo100M: Learning a Text-Video Embedding by Watching
  Hundred Million Narrated Video Clips", arXiv:1906.03327 (baseline
  dataset).
- Han et al., "Temporal Alignment Networks (TAN) for Long-term Video",
  arXiv:2204.02968 — quantifies that only ~30% of HowTo100M narrations
  are visually alignable, only ~15% timestamp-clean.
- Shvetsova et al., "HowToCaption: Prompting LLMs to Transform Video
  Annotations at Scale", ECCV 2024
  (<https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07249.pdf>).
- "Multi-Sentence Grounding for Long-term Instructional Video",
  arXiv:2312.14055 — HTM-370K subset, same alignment failure modes.
- "ShowHowTo: Generating Scene-Conditioned Step-by-Step Visual
  Instructions", arXiv:2412.01987.
- Ko et al., "Video-Text Representation Learning via Differentiable Weak
  Temporal Alignment", arXiv:2203.16784.

## One-line summary

Every large-scale narrated-cooking-video dataset the field relies on
inherits three failure modes from ASR-derived captions: recognition
errors, non-descriptive speech, and temporal misalignment. Only ~15%
of narrations are naturally well-aligned with their frames.

## Why this matters for us

Our current stack has *no* ASR path. When we add one (we will, for
the YouTube-CC-BY adapter and PeerTube long-form videos), we will hit
the exact same wall. We should design the caption schema now, and
document explicitly that we will not use raw ASR as supervision.

Second-order implication: **Common Crawl `schema.org/Recipe` blocks
are qualitatively different**. Structured `recipeInstructions` are
already step-ordered, non-colloquial, and manually authored. Our
`common_crawl` adapter is thus not "one of four data sources" — it is
the *only* source in the current pipeline whose text is not going to
suffer from the HowTo100M alignment trap. This is a real research
edge worth measuring.

## What to steal

1. **LLM-summarize-then-realign.** Both HowToCaption and ShowHowTo
   replace raw ASR with an LLM-summarized "step list" and re-align
   to frames post-hoc. This is what we should do the moment we start
   ingesting ASR. Ship the *schema* now:
   `VideoRecord.recipe_steps` already exists — extend it (in a future
   schema PR) with `steps_source ∈ {upstream_structured, asr_llm,
   human}` so provenance-of-steps is queryable.
2. **HTM-Align style manual eval subsets.** Even a tiny (100-record)
   hand-checked alignment set gives us a leaderboard-style metric. The
   `compare/` harness should learn to accept an "aligned truth" file
   and compute step-alignment accuracy against it.
3. **Category-based ingestion.** HTM-370K uses only "Food &
   Entertaining" (32% of HowTo100M). This confirms the domain-narrow
   focus of `AGENTS.md` is compatible with SOTA practice.

## What to not steal

- **HowTo100M itself.** YouTube TOS forbids downloading, and its
  license status per-video is inconsistent. We can *cite* it for
  methodology and never mirror its media.
- **Auto-aligned (HTM-AA) narration timestamps as gold supervision.**
  They are still noisy; they should be treated as weak labels only.

## Follow-ups filed

- Design `steps_source` enum in the schema PR that also adds
  `clip_id`. Keep out of this iteration.
- Add a "recipe-JSON-LD-is-not-HowTo100M" benchmark: measure
  step-count and mean-step-length on `common_crawl` fixtures and put
  the number in the daily comparison report. This is a strong argument
  we should be able to make quantitatively soon.
