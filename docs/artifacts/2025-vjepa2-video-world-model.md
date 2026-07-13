# V-JEPA 2 — self-supervised video world model (Meta, 2025)

- **Source.** Assran et al., *V-JEPA 2: Self-Supervised Video Models Enable
  Understanding, Prediction and Planning*, arXiv:2506.09985 (2025).
  Model + code at `github.com/facebookresearch/vjepa2` (weights CC-BY-NC 4.0;
  code under a permissive license).
- **Claim we care about.** ~1M hours of unlabeled internet video are enough
  to pretrain an action-free encoder that, after ≤62 h of action-conditioned
  post-training, plans manipulation zero-shot on real robots. Web-scale
  *video breadth* dominates any single curated benchmark.

## Method summary

- Encoder is a ViT-{L,H,g} operating on 3D tubelets with 3D-RoPE; predictor
  is a smaller transformer trained via masked-latent prediction (L1 to EMA
  target) — no pixel reconstruction.
- Pretrain mix "VideoMix22M": SSv2, Kinetics, HowTo100M, YT-1B, ImageNet.
  Progressive resolution: 16×256² → cooldown 64×384² for ~8× compute
  savings on the long-context stage.
- Post-training (V-JEPA 2-AC) adds a latent action head, trained on <62 h of
  Droid Franka trajectories with an L1 + 2-step rollout loss. Planning is
  vanilla CEM in latent space, receding-horizon.

## What it changes for us

1. **Breadth > per-clip length.** Our current heuristic peaks quality at
   5-minute clips; V-JEPA 2's masked-tubelet objective benefits more from
   *diverse* short clips than one long one. Add a second quality mode
   (`mode="jepa"`) that rewards clips in the 8–60 s band, matching the
   sampling window V-JEPA 2 uses at pretraining time.
2. **Content-mode gating.** V-JEPA 2's biggest wins are on motion-heavy
   benchmarks (SSv2, EK-100). Add a "motion prior" — currently we can only
   estimate it from `keywords`/`recipe_steps` (procedural signal); TODO
   ticket to compute a temporal-difference proxy once we allow ~64-frame
   downloads for a sampled 1 % of records.
3. **Action-free first.** Confirms that we do not need paired
   action/reward data at collection time. Our license-clean video-only
   corpus is directly usable for stage-1 pretraining; robot data is a
   separate, small addendum. Keep robot-data sources out of the
   allowlist for now — they add ToS complexity for no marginal gain.
4. **Progressive resolution.** Justifies storing `width`/`height` and a
   downstream `native_fps` field. We already store the former; add
   `native_fps` as a follow-up (already covered by `fps`).

## Risks / disagreements

- Their pretraining mix is *not* license-clean (YT-1B, HowTo100M scrape
  YouTube). A comparable public replication under our constraints will need
  ~10× more sources, not just one big one. This is exactly the argument for
  the systematic-source-comparison harness we already ship.
- L1 masked-latent loss is *scale-hungry*; on a small legally-clean corpus
  we may need contrastive pretraining as a bridge. Track as an
  experiments-only note; no code change today.
