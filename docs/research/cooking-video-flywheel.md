# The cooking-video flywheel — long-form essay

> Adversarial-Agent's argument for why and how to build a license-clean,
> world-model-useful cooking-video corpus from the open web in 2026.

## 1. Why cooking video, why now?

Cooking is the densest *legal-to-acquire* corner of human-physical-task
video, for three convergent reasons:

1. **Demonstrative narration is universal.** Recipes are explained while
   performed. ASR transcripts have unusually high alignment to the visual
   action — the HowTo100M premise generalizes to license-clean sources.
2. **The action vocabulary is rich and physical.** Cooking is a near-ideal
   probe for world models: object permanence under occlusion (lid on pot),
   state changes (raw → cooked), tool use, multi-step planning, and
   bimanual manipulation, all in a small set of scenes (kitchens).
3. **The license-clean tail is non-trivial.** Wikimedia Commons hosts
   tens of cooking videos. Internet Archive's home-economics films and
   modern community uploads add hundreds of hours. PeerTube cooking
   communities are growing. Vimeo CC search returns thousands of hits.
   This is small compared to YouTube, but it is *enough* to bootstrap
   a frontier-grade pipeline and prove the methodology, after which we
   can scale across domains.

## 2. Why not YouTube

Covered exhaustively in `docs/artifacts/legal-landscape.md`. Short
version: YouTube is, in 2026, the source with the highest legal risk per
byte of any major video corpus, due to *Chmura v. Snap* and the April 2026
creator class actions. YouTube CC tagging does not override the
platform's ToS prohibition on automated download (V3C paper, 2018, made
this argument first; the 2026 cases turn on the same fact pattern but
under DMCA §1201 anti-circumvention).

For us, this means: **YouTube is a discovery hint, not an acquisition
target.** We use YouTube-derived ID lists (HowTo100M, etc.) only as
prompts to *go look for license-clean equivalents elsewhere*.

## 3. The flywheel, in one sentence

> *Discover license-clean candidates, segment and score them, dedup
> against eval sets and prior shards, and ship a manifest whose value
> per byte is measured by held-out world-model probes — not by aesthetic
> alone.*

## 4. The four moats we are building

1. **A license-clean source registry**, with per-source adapters and a
   confidence-aware license string. This is unsexy and 90% of the
   long-term value.
2. **A reproducible filter chain** (Summer-22B-style), versioned via
   `pipeline_version`, so every shard is bit-for-bit reproducible from
   the manifest.
3. **A "world-model utility" learned filter** (planned v2). Trained on
   the ablation: did including this clip in pretrain improve next-frame
   loss on a held-out probe? This is the equivalent of DCLM's fastText
   filter for video.
4. **A first-class takedown / opt-out path.** Every shard carries
   contact information and a stated removal SLA. This is a moat
   because it is the *only* way to operate license-cleanly at scale —
   when (not if) an uploader opts out, we must be able to remove their
   content from every downstream shard within hours.

## 5. The egocentric gap and how to close it

The hardest single gap is egocentric data. EPIC-KITCHENS, HD-EPIC, and
Ego4D are research-license-only. DreamDojo's 44k-hour egocentric corpus
is internal. Without egocentric coverage, the cooking corpus is
third-person-biased and underperforms for embodied-agent fine-tuning.

Three potential approaches, ranked by my prior on feasibility:

1. **Federated opt-in collection on PeerTube.** Stand up (or partner
   with) a PeerTube instance for "cook-along POV" creators who explicitly
   choose CC-BY or CC0. Grant: a small data subsidy in exchange for a
   broad license. Risk: chicken-and-egg (no creators yet); cost: low
   monetary, moderate community-management.
2. **Wikimedia Commons egocentric upload campaign.** Coordinate with
   Wikimedia volunteer chapters; their existing infrastructure handles
   licensing, attribution, and takedown. Risk: throughput is governed
   by volunteer interest, not engineering. Cost: ~zero monetary.
3. **Government / public-broadcaster open archives.** USDA, NHS, and
   public-broadcaster cooking shows occasionally have open-license
   episodes; egocentric examples are rare but not absent (cooking-show
   B-roll from POV cameras). Risk: small absolute volume; cost: zero
   monetary.

None of these alone closes the gap. Together, they could plausibly
yield hundreds of hours of egocentric license-clean cooking video over
a horizon long enough to matter. We track this as the highest-leverage
data-collection bet in the repository.

## 6. What "robust and frontier" means for us, operationally

- **Robust** = every shard is reproducible from a manifest, with a
  pinned `pipeline_version`, a documented filter chain, and a takedown
  SLA. If a key dependency disappears, we can replay collection on the
  same canonical URLs.
- **Frontier** = our filter chain reflects the 2026 state of the art
  (Summer-22B / Panda-70M / DreamDojo references), our utility metric
  is *world-model loss on held-out probes* rather than aesthetic
  alone, and we publish per-source license-confidence + bias audits
  that no public dataset currently provides.

## 7. The evaluation moat

Pretraining-data quality is only meaningfully measurable through
downstream evaluation. We pre-commit (literally and figuratively) to the
following held-out probes, all license-clean:

- **Wikimedia Commons holdout**: 10% of every Commons cooking-video
  collection, never used for training, only for next-frame and
  caption-retrieval probes.
- **Synthetic action probes**: programmatic scenes (e.g. ffmpeg-rendered
  knife-and-onion gradient transitions) where the "right answer" is
  computable, used for sanity-check next-frame loss curves.
- **Open partner sets** (when available): explicitly-licensed academic
  splits whose evaluation use is permitted.

We *deliberately do not* benchmark against EPIC-KITCHENS or YouCook2 in
the headline numbers, because (a) they are research-license-only and
(b) their videos can leak into Wikimedia / Internet Archive uploads in
unpredictable ways. Treat them as unofficial cross-checks, not
headline benchmarks.

## 8. Critique of this plan from an opposing perspective

A reviewer who disagrees with this approach would argue:

- *"You're hamstringing yourself on legality; the labs that win in 2026
  will have absorbed the litigation cost."* Counter: the 2026 cases are
  not yet decided, and a license-clean pipeline is the only one that
  survives every plausible outcome. The methodology *also* generalizes
  to non-public-but-licensed corpora (e.g. partner-licensed home cooks)
  in a way that an `yt-dlp` pipeline does not.
- *"The volume difference is too large; license-clean is a toy."*
  Counter: the bottleneck for world models is not raw bytes, it is
  *useful* bytes. DCLM and Summer-22B both show that careful curation
  beats raw scale. We are betting on the same trend in video.
- *"You'll never close the egocentric gap legally."* Counter: §5
  outlines three concrete legal paths. None alone closes it; together
  they are credible.

## 9. The single most important next step

Build the **per-source adapter for Wikimedia Commons cooking videos**
end-to-end through the pipeline (discover → license_check → segment →
score → dedup → shard) on the existing 75-ish-video corpus. This is
small enough to finish quickly, broad enough to exercise every stage,
and generates a license-clean baseline shard we can extend from.

After that, the per-source adapter for **Internet Archive
community/Prelinger cooking footage** is the highest-leverage second
adapter.
