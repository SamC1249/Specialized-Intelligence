# HD-EPIC — Highly-Detailed Egocentric Video Dataset (CVPR 2025)

> Source: Perrett et al., "HD-EPIC" (CVPR 2025;
> <https://hd-epic.github.io/site/>).
> Notes captured: 2026-06-24 by Adversarial-Agent.

## TL;DR

41 hours, 9 kitchens, **in-the-wild unscripted** egocentric cooking video
collected over 3 days per participant, with digital-twinning of fixtures
and gaze priming. Annotations: 69 recipes, 59K fine-grained actions, 51K
audio events, 20K object motions, 37K segmentation masks lifted to 3D.

This is the densest single annotation budget for cooking egocentric video
in 2025–2026. ~263 annotations per minute.

## License posture

**CC BY-NC 4.0.** Non-commercial only. Commercial use requires reaching
out to UoB (`uob-epic-kitchens@bristol.ac.uk`). This matches EPIC-KITCHENS
itself and Ego4D — the egocentric-cooking gold standard *as a class* is
research-license-only.

Implication for us: HD-EPIC **cannot ship in our shards** if any
downstream use is commercial. It is, however, an excellent **eval and
contamination-source** dataset.

## Why it matters

1. **Density beats scale.** HD-EPIC has fewer hours than EgoExo4D or
   Ego4D but >250 annotations/min. Gemini Pro scores 37.0% on its VQA
   benchmark — meaning current frontier VLMs are *not saturated* on
   fine-grained kitchen perception. This is a tractable evaluation
   surface.
2. **Validates "in-the-wild" matters.** Recipe videos that are *trimmed,
   edited, sped up* (i.e. most online how-tos) lose ingredients-fetching,
   weighing, prepping. A world model trained only on edited content
   will have a strong temporal-edit prior baked in — bad for action-
   conditioned rollout fidelity.
3. **3D digital twin of the kitchen** is a free supervision signal we
   *could* in principle approximate cheaply with mast3r / MASt3R-style
   reconstruction over CC-clean kitchen footage.

## Adversarial concerns

- **Contamination risk for evaluation.** HD-EPIC participants overlap with
  EPIC-KITCHENS participants. If we ever use either as a probe, we must
  blocklist the *union* of video IDs and near-duplicate keyframes.
- **CC-BY-NC ≠ "training-clean."** Even for research-only world-model
  pretraining, the NC clause is interpreted differently across
  jurisdictions. Treat as research-only and do not include in default
  shards.
- **Tiny per-task budgets.** 41 hours is great for evaluation, useless
  for pretraining a 2B-param world model in isolation. The role of
  HD-EPIC in our pipeline is **target distribution + eval set**, not
  pretraining mass.

## Action items

1. **Add `hd_epic` to `eval_blocklist.jsonl`** when we have keyframe
   pHashes — *do not yet bring HD-EPIC bytes in*, since we cannot legally
   redistribute and our pre-commit / CI should not depend on the user
   having a research-license-only download.
2. **Use HD-EPIC's annotation taxonomy** (fetch / prep / weigh / cook /
   plate) as a target for our captioning step. The taxonomy itself is
   factual and not copyrightable; we can adopt it.
3. **Probe-only inclusion when we can secure research approval.** If we
   later add a research-only evaluation track, HD-EPIC fits there.

## Key references

- CVPR 2025 poster page: <https://cvpr.thecvf.com/virtual/2025/poster/33586>
- HD-EPIC project page: <https://hd-epic.github.io/site/>
