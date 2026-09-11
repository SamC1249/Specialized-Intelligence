# Sekai2 + SolarWM — provenance-first data engines

- **Citations.**
  - *Sekai2: From World Exploration to Interactive World Modeling*,
    arXiv:2608.09449 (2026).
  - *SolarWM: Open Data and Scalable Training for Long-Horizon Video
    World Models*, arXiv:2609.02886 (2026). Releases 1.43M canonical
    clips from 10 datasets under a unified schema.

## One-paragraph summary

Both papers treat *the data engine itself* as the release, not just the
resulting weights. SolarWM explicitly decouples source-level
preprocessing from mixture construction so that researchers can change
filter thresholds, sampling ratios, and source weights without redoing
the expensive per-source pass. Sekai2 uses a manifest-driven filtering
pipeline with independent gates (optical-flow motion, OCR/HUD/watermark
detection, camera-pose validity, semantic-annotation validity) and
retains rejected samples with machine-readable rejection reasons.

## Why it matters to Specialized-Intelligence

- These are the *reference implementations* of our "Comparison-First
  Rule" (AGENTS.md). Every stage's decision is logged with a reason,
  every mixture change is a config diff, no downstream re-run of the
  slow parts.
- SolarWM's "keep rejected samples with reasons" is directly
  applicable: today we silently drop non-video Wikimedia results and
  non-CC PeerTube results. We should keep them with a `rejected=True`
  flag and a `rejection_reason` so we can measure retention and change
  thresholds without re-fetching.
- Provenance requirements match ours (AGENTS.md §2). We should extend
  `Provenance` to include the extractor's config hash, not just its
  git SHA, so a threshold change is provably reflected in the record.

## Concrete ideas to steal

- Add a `RejectionReason` enum (`license_unknown`, `wrong_media_type`,
  `duration_out_of_range`, `resolution_below_min`, `dedup_collapsed`,
  `text_below_min`) and a `rejected: bool = False` field on
  `VideoRecord`. Aggregation counts rejections per reason per source.
- Add `Provenance.config_hash` (SHA-256 of the extractor's serialized
  config). CI test: two runs with the same config produce the same
  hash; changing any threshold changes it.
- Split `compare.harness` into a `pipeline` module that takes an
  ordered list of `Stage` objects, each with a
  `apply(records) -> tuple[kept, rejected]` interface. This lets us
  add/reorder/A-B-test stages without touching the harness.
- Emit a `manifest-*.json` alongside every `compare-*.json` that lists,
  per (source, stage), the input count and output count. This is a
  cheap way to reach "reproducible with rejection reasons" without
  storing every rejected record.

## Risks / gotchas

- Storing rejected records grows the artifact size. Solution: store
  only the (id, rejection_reason) tuple, not the full record.
- SolarWM's "reconfigurable mixture" concept implies eventual training;
  we are still at the URL+metadata stage. Do not over-engineer the
  pipeline until we have a concrete downstream consumer.
