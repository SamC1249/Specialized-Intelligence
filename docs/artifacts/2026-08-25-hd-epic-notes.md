# HD-EPIC / Ego2World as a target distribution

Author: Coding-Agent · Date: 2026-08-25

HD-EPIC (2025) and Ego2World are egocentric procedural video benchmarks.
They are *not* legal data sources for our corpus, but they *are* useful
as a **target distribution**: which of our metadata signals predict a
cooking video will look, feel, and be labelled like an HD-EPIC clip?

## Salient HD-EPIC properties (from published stats)

- Ego / third-person mix: **95% egocentric**.
- Action taxonomy density: ~1 verb per 3 seconds on average.
- 4K, 60 fps, hands-visible.
- Full-take recording; no jump cuts.
- Rich narration (speech-to-action alignment is a first-class label).

## Which of our signals correlate?

| HD-EPIC property | Metadata signal we already compute |
| ---------------- | ---------------------------------- |
| High resolution  | `resolution` (weight 0.20 baseline) |
| Full-take        | `shot_density` heuristic (new, `procedural.py`) |
| Narration        | `audio_present` (new) |
| Verb density     | `cooking_verbs` count (new) |
| Landscape framing | `aspect_ratio` (new) |
| Ego framing      | Not currently captured. Placeholder metric idea: `POV_hint` — regex on title/description for `"POV"`, `"first-person"`, `"egocentric"`. |

## Followups to move closer to the target distribution

- Ship a `POV_hint` signal (regex + simple keywords) and A/B it in
  `WEIGHTS_EXPERIMENTAL`.
- Once we can download bytes: run one HD-EPIC pretrained action-
  recognition head on a small sample of our downloaded clips and
  compare `top-1 verb ∈ HD-EPIC taxonomy` rates per source.
- Formalise "procedural-ness" as a scalar target computed from the
  above signals; report it on the `__deduped__` row alongside
  `mean_quality`.
