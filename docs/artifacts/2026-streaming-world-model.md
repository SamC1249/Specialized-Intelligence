# Streaming World Models — physical prior distillation (arXiv 2608.07981)

- **Citation:** *Distilling Physical Priors into Streaming World
  Models.* arXiv 2608.07981 (2026).
- **Permalink:** <https://arxiv.org/html/2608.07981>

## One-paragraph summary

The paper collects **120 K real-world physical-interaction video clips**
across four categories (rigid-body dynamics, body deformation, fluid
phenomena, "other physical processes"), each with structured
descriptions of object properties, state changes, and causal event
sequences. Collection pipeline: candidate videos pulled from *public
video platforms and open datasets — YouTube, Pexels, WISA — with
process-oriented queries*, shot-segmented with TransNetV2, near-dup
removed, then filtered by RAFT (motion quality), OpenNSFW2, DOVER
(aesthetic quality), and clarity/text detection. Retained clips are
category-classified, class-balanced, and finally annotated by
Qwen3-VL-235B-A22B; a human audit team samples and corrects VLM
outputs. The world model is then trained with online RL over video
generation conditioned on the structured descriptions.

## Transferable to `specint`

- **Multi-stage filter cascade is the right shape** for our quality
  scorer. Today `score_record` is a *flat* weighted sum. It should
  become a *cascade*:
  1. legal gate (license clean),
  2. cheap metadata heuristics (duration, resolution, text density),
  3. thumbnail-only signals (aspect, blur — future),
  4. per-clip signals (motion, aesthetics — future, VLM-gated).
- **Class balancing** matters. Add a `category` field or infer it from
  keywords, and compute a per-category `n_records` in
  `BenchmarkResult` so we can detect a corpus that is 90 % pasta and
  10 % of everything else.
- **Pexels is in our legal allowlist gap.** Pexels licence is
  "free to use, modify, and redistribute even commercially, but
  attribution appreciated" — this is close to CC0-equivalent and
  needs its own adversarial audit before adding an adapter.
- **Human-audit loop.** The paper's *audit-and-refine* step is
  worth mirroring as a lightweight `python -m specint audit` command:
  sample K records per source, present metadata + thumbnail, capture
  a 1-5 label, and correlate with `quality_score` to detect scorer
  drift.

## NOT transferable

- YouTube ingestion in the paper is *not* CC-filtered. We ingest
  YouTube only under the CC-BY (`videoLicense=creativeCommon`) filter.
- The heavy VLM/RL machinery is out of scope for a data-collection
  repo; keep it downstream.

## Adversarial notes

1. If the paper's central assumption — that filtered raw internet
   video is a rich source of physical priors — holds, then our
   cooking narrow-focus is generalisable *for free* to other physical
   verticals (welding, soldering, gardening, chemistry demos). Our
   `BaseSource` abstraction is already vertical-agnostic; the *queries*
   in `SourceQuery` are the only cooking-specific artifact.
2. Their 120K clips came from mixed-licence sources. If we build a
   parallel corpus at even 10K clips but *fully licence-clean*, it is
   more legally durable — even if smaller. This is the correct
   trade-off to advertise in the transparency summary.
