# CaptainCook4D + Qualcomm Interactive Cooking

- **CaptainCook4D:** DMLR Workshop @ ICML 2023. Procedural cooking
  video with explicit error / mistake annotations. GoPro + HoloLens +
  depth + spatial + audio. <https://captaincook4d.github.io/>.
- **Qualcomm Interactive Cooking:** arXiv 2511.21998 (Nov 2026).
  Benchmark built on CaptainCook4D for live, step-by-step coaching:
  densely annotated, timed instructions + feedback messages, with mistake
  alerts precisely timestamped to their visual occurrence.

## One-line summary

The frontier work on cooking-video world models is no longer about
"recognise the recipe"; it is about **detecting mistakes and
replanning in real time**. Our current quality rubric does not reward
error-containing video at all.

## Why it matters to us

- **Negative examples are training-valuable.** Current scorer penalises
  sources that lack clean step sequences. But a video containing a
  *recoverable error* ("oops, over-salted — add potato") is strictly more
  informative for world models than a clean execution, because it exposes
  a counter-factual state transition. Our scorer should not downweight
  such content.
- **Streaming / interactive evaluation changes what "procedural density"
  means.** Qualcomm's benchmark asks whether a VLM can speak at the
  *right time*. Our fixtures should eventually carry per-second
  timestamps, not just a flat step list.
- **CC4D's modalities (depth + spatial + audio) remind us:** we discard
  audio today. See plan-2026-11-12 H12.

## What we can / can't copy

- **Can:** The *axes* of what a good procedural video looks like
  (instructions, feedback, mistake alerts). Schema: `(timestamp, kind ∈
  {instruction, feedback, mistake}, text)`.
- **Can't:** CC4D's video is CC BY-NC-SA 4.0 per the authors' own site
  (non-commercial), which fails our "no NC" rule. We can cite and
  benchmark against but cannot train on it.

## Concrete actions

1. In `records.py`, reserve `annotations: list[Annotation] | None = None`
   where `Annotation` is `(timestamp_s: float, kind: Literal["step",
   "feedback", "mistake"], text: str)`. Do NOT ship in this PR — captured
   for the next Coding-Agent to avoid a schema migration churn.
2. Add a `procedural_density` quality component now (H4) that at least
   graduates us from binary `has_steps` → graded density. This is the
   smallest non-trivial step toward the CC4D axis.
3. Stop treating "no recipe_steps" as `quality 0.0 for has_steps` →
   future: treat it as `uninformative` and reweight. Captured for next
   plan.
