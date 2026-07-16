# HowTo100M (Miech et al., ICCV 2019)

- Paper: https://openaccess.thecvf.com/content_ICCV_2019/papers/Miech_HowTo100M_Learning_a_Text-Video_Embedding_by_Watching_Hundred_Million_Narrated_Video_Clips_ICCV_2019_paper.pdf
- Project: https://www.di.ens.fr/willow/research/howto100m/

## Claim

Instructional narration on YouTube is a scalable, weakly-supervised
signal for text-video alignment: 136M clip-caption pairs sourced from
1.2M "how to X" videos across 23,611 visual tasks (cooking, DIY, home
care, gardening, fitness, …). The tasks are drawn from the WikiHow
ontology, restricted to physical/visual verbs (make, build, change).

## Evidence

- Ablation shows their text-video embedding trained on HowTo100M
  transfers to YouCook2, MSR-VTT, LSMDC — SOTA at time of publication.
- Selection pipeline: WikiHow taxonomy → English YouTube search →
  filter `views>100`, `duration<2000s`, dedup by video ID.
- Weakness: **license is "not specified"** and the pipeline actively
  downloaded copyrighted YouTube video. Their release is URL + features
  only, transferring the licensing risk to reusers. Our project cannot
  emulate this end-to-end.

## Steal

1. **WikiHow taxonomy as a seed-term generator.** WikiHow itself is
   CC-BY-NC-SA (non-commercial), so we can't redistribute WikiHow
   content, but the *list of visual task titles* is a factual
   compilation — safe to use as search queries against our permissively
   licensed sources. Ship a `src/specint/quality/task_ontology.py`
   that carries a curated CC-BY subset (cooking domain first).
2. **Verb-filtering rule.** Restricting to physical verbs is a
   metadata-only proxy for procedural content. We can apply the same
   filter to Common Crawl `Recipe.name` and Wikimedia titles for free.
3. **"Related videos" bootstrap is a trap.** They deduplicated only by
   video ID; the same recipe re-uploaded is not caught. Confirms H3 in
   the 2026-07-16 plan: we need SimHash-level dedup, not ID dedup.

## Implications for specint

- Feeds `docs/plan-2026-07-16.md` → Sources (H2) → `wikibooks_cookbook.py`
  and Openverse adapters get a legal seed-term list.
- Feeds Dedup (H3): our design must catch re-uploads, not just id
  collisions — SimHash on title+description+host is the minimum viable
  filter.
- Anti-feed: **do not** copy the "just search YouTube and download"
  pipeline. Our YouTube slot in the allowlist is metadata-only via
  `videoLicense=creativeCommon` and gated behind an API key.
