# 05 — Procedural-density scorer (metadata-only)

**Status:** proposed (Priority-B in `plan-2026-10-12.md`).
**Hypothesis served:** H5 (procedural density).

## Problem

Current `quality.metrics` has a binary `has_steps` component that
rewards *any* non-empty `recipe_steps` list. That's a weak proxy:

- A 3-step "preheat oven / mix / bake" entry scores identically to a
  12-step entry with timed sub-steps.
- A talking-head video with a long description but no step structure
  gets zero credit even if it names every technique.
- Non-English recipes are penalised purely because the lexicon is
  implicit in the model's priors, not in a committed artifact.

For world-model training we specifically care about **irreversible,
state-changing actions** ("sear", "fold", "emulsify", "deglaze")
rather than talk about food. That's a signal we can get from
metadata alone with a committed verb lexicon.

## Priors we're borrowing

- **COIN** / **HowTo100M** / **YouCook2** show that cooking action
  verbs are a small (~400) closed set that covers >90% of recipe
  text. We're not training on those datasets — we're using the fact
  that the vocabulary is small and auditable.
- **Panda-70M** desirability filtering excludes "still foreground",
  "tiny camera movement", "screen-in-screen", "computer screen
  recording". Those are *frame-level* signals we can't yet compute.
  But the project's observation that **80.5%** of raw-crawl video is
  undesirable is exactly why metadata triage matters: we want to
  dodge the 19.5% quality floor before paying for compute.
  Reference: [snap-research/Panda-70M][panda].

## Proposed design

- New file `src/specint/quality/cooking_verbs.txt` — one lemma per
  line, lowercase, sorted. Committed and auditable. Seed from COIN
  and manual review.
- New scoring function in `src/specint/quality/metrics.py`:
  ```python
  def _score_procedural_density(record: VideoRecord) -> float:
      text = " ".join(
          [
              record.title,
              record.description,
              *record.recipe_steps,
          ]
      ).lower()
      tokens = re.findall(r"[a-zA-Z]+", text)
      if not tokens:
          return 0.0
      verb_hits = sum(1 for t in tokens if t in COOKING_VERBS)
      return min(1.0, verb_hits / 20.0)
  ```
- Add to `WEIGHTS` with a documented rationale; demote `has_steps`
  weight from 0.15 to 0.05 (keep it as a diversity signal, not a
  main driver).
- Fixture: `tests/fixtures/procedural/labelled_50.jsonl` — 50
  synthetic `VideoRecord`-shape rows, each tagged
  `procedural: True|False` by hand. Test asserts AUC ≥ 0.80 using a
  deterministic pure-Python ROC implementation (no scikit-learn
  dependency).
- Multilingual follow-up (deferred): a per-language supplementary
  lexicon under `cooking_verbs.<lang>.txt`, chosen by
  `record.language`.

## Risks (adversarial)

- **Lexicon captures Western cuisine bias.** A `cooking_verbs.txt`
  seeded from English cookbooks will score Japanese "mushi" (蒸し,
  "steam") videos 0.0. The 50-clip labelled fixture MUST include at
  least 10 non-English clips. If AUC drops below 0.60 on the
  non-English subset, the lexicon has to grow.
- **Keyword spam.** Recipe aggregators sometimes stuff "sear deglaze
  reduce" into titles for SEO. The saturation at 20 verb hits caps
  this and we add a diminishing-returns tail.
- **Correlates with length, not quality.** Longer text has more words
  of any kind. Normalize by `log(1 + len(tokens))` once we have
  evidence that length is correlated with the score (next cycle).

## Takeaway for specint

Metadata-only procedural density is cheap, debuggable, and
immediately generalisable: swap `cooking_verbs.txt` for
`surgery_verbs.txt` to cover a different "difficult video" domain
without changing the scorer. It's the highest-leverage upgrade to
`quality/metrics.py` that respects the metadata-only budget.

[panda]: https://github.com/snap-research/Panda-70M
