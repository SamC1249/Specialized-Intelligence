# Metadata-only detection of AI-generated ("slop") recipe pages

- Graphite (2026) — sampled 65K English articles from Common Crawl
  2020-01 → 2025-05 with the Surfer AI-text detector; ≥ 50 % of newly
  published articles from Nov 2024 onward were LLM-authored under a
  ≥ 50 %-generated threshold. Human FPR of the detector ≈ 4.2 %,
  LLM-missed rate ≈ 0.6 %.
- Columbia SIPA IGP report, *AI Slop and the Information Ecosystem*
  (Jun 2026) — canonical policy framing: slop is a subset of AIGC,
  characterized by high volume, low depth, and platform-incentive
  alignment rather than authorial intent.
- New York Times business desk (Jun 2026) — People Inc. (Allrecipes,
  Food & Wine, Southern Living) built a 40,000 sq-ft Birmingham test
  kitchen expressly to *distinguish human recipe development from AI
  slop*. Editorial signal: reputable publishers now brand their human
  provenance.
- Futurism / The Cut (2026) — reporter case study of AI-generated
  recipes: physics-defying voiceovers, ingredient hallucinations,
  frequent verbatim copying from Minimalist Baker. Notes the
  characteristic "generic phrasing, missing About-Me, warped-image"
  fingerprint.

## Why this belongs in our pipeline today

Our current `quality/metrics.py` component `text_density` rewards
long titles + descriptions + `recipe_steps`. LLM-authored recipe
pages are typically *longer* than human-authored ones (they pad SEO
prose), so the current scorer actively promotes them. This is the
adversarial regime the Graphite / Columbia data describes and we are
walking into it eyes-open.

## Metadata-only signals that discriminate

None of these require downloading the video or the page HTML beyond
what our Common Crawl adapter already extracts:

| Signal                            | Direction | Notes                                                                    |
| --------------------------------- | --------- | ------------------------------------------------------------------------ |
| `author` absent                   | +slop     | Human food blogs almost always have an About-Me.                         |
| `datePublished` after 2024-01     | +slop     | LLM content farms scaled post ChatGPT plugins / GPT-4o.                  |
| `dateModified` absent             | +slop     | Slop is fire-and-forget; human bloggers revise.                          |
| `commentCount` absent / zero      | +slop     | Slop has no readers.                                                     |
| Title matches `list-N-*` regex    | +slop     | "10 Best...", "5 Easy...", "The 7 Most Underrated..." are LLM-typical.   |
| Recipe steps count in [8, 14] AND step lengths all in [80, 220] chars | +slop | LLMs generate suspiciously regular step lengths.                         |
| Boilerplate n-grams present       | +slop     | "Once you've done that, simply enjoy", "Now you have a delicious...".    |
| Host TLD ∈ new-gTLD               | +slop     | `.recipes`, `.cooking`, `.chef`, `.blog` disproportionately farm slop.   |
| `recipe_steps` contain unit typos | -slop     | Humans mis-type "tsp" as "teasp"; LLMs are grammatically pristine.       |
| Photo EXIF absent from JSON-LD    | +slop     | Slop lifts stock imagery; human bloggers keep EXIF.                      |

None of these is a *proof*. Together, weighted, they should meet
the adversarial hypothesis's ≥ 0.75 AUC bar on a small labelled
fixture. We keep the scorer rule-based (no ML) so it is auditable
and reproducible offline.

## What the literature does *not* solve

- Detectors are notoriously miscalibrated — GPTZero, DetectGPT, and
  even fine-tuned RoBERTa detectors show 3-30 % FPR on human text
  from underrepresented dialects (Liang et al. 2023). We accept
  higher FPR in exchange for having a transparent per-signal
  breakdown that a reviewer can override manually.
- Content-farm hosts routinely edit LLM output to insert typos and
  boilerplate to defeat detectors. This is a moving target; treat
  the scorer as a *shifting soft filter*, not a permanent label.
- Video slop (AI-generated cooking TikToks) requires per-frame or
  audio-side signals — deferred until we have a media store.

## Concrete deliverable pointer

Maps to plan 2026-07-17 deliverable 3 (H6): `quality/ai_slop.py`,
hand-graded fixture under `tests/fixtures/ai_slop/`, additive
`n_ai_slop_flagged` counter in the compare payload, and rank
correlation ≥ 0.7 as the acceptance bar.

## Falsifier

If the rule-based scorer's rank correlation on the hand-graded
fixture is < 0.5, or its precision at threshold 0.6 is < 0.5, we
should either enrich the signals or drop AI-slop detection to a
per-source blacklist of known content-farm hosts and revisit when
we can afford a proper detector.
