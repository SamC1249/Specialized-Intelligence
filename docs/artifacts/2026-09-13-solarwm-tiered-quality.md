# SolarWM: Tiered, Reversible Quality Filtering for Video World Models

- Paper: *SolarWM: Open Data and Scalable Training for Long-Horizon Video
  World Models* (arXiv:2609.02886, 2026).
- URL: https://arxiv.org/pdf/2609.02886 ; HF page:
  https://huggingface.co/papers/2609.02886
- License of the artefact: open release of processed corpus, pipeline,
  weights, and framework (no paywall).

## Why it matters to us

SolarWM is the most rigorous open recipe published so far for turning a
heterogeneous pile of video into a training-ready world-model corpus. It
converts 1.43M canonical clips from ~10 upstream datasets into a single
frame-aligned "contract" (observations, metric camera geometry, captions,
quality metadata, selection decisions, provenance). That contract is the
exact analogue of our `VideoRecord` + `BenchmarkResult`, and there are two
design choices we should copy today.

### 1. Three physical quality tiers, not a scalar

SolarWM freezes a versioned per-dataset policy that produces three
disjoint labels:

- **`xhigh`** — passes the "kept" rule AND a stricter "promotion" rule.
- **`high`** — passes the "kept" rule only.
- **`rejected`** — retained with an explicit `failure_reasons` list so
  downstream researchers can audit or re-admit them.

Rejections are **retained** rather than deleted; every metric named by a
rule must be present, finite, and correctly typed. This makes threshold
changes reversible without re-running the expensive preprocessing.

**Actionable for specint.** Replace our single `quality_score ∈ [0,1]`
with a companion `QualityTier` enum + `failure_reasons: list[str]`. Keep
the scalar for backward compat. New CLI flag `--tier xhigh` filters in
`compare` without changing the underlying records.

### 2. Decouple source processing from mixture construction

SolarWM's engine explicitly separates *per-source normalisation* from
*training-mixture design* so a researcher can change filtering criteria,
sampling ratios, or split definitions "without rerunning the
computationally intensive source preprocessing." This is the same
separation-of-concerns we already have (`sources/*` → `quality/*` →
`compare/*`), but we currently *conflate* filtering with the score, which
means every threshold change re-runs the score pass.

**Actionable.** Filtering rules go in a new `src/specint/quality/rules.py`
as pure functions returning `(tier, reasons)`. The `metrics.py` scorer
stays scalar-only. `compare.harness` composes both.

## Quotes to keep honest with

> "quality tiers, not an irreversible definition of valid data. Users can
> change thresholds, disable a filtering rule, or promote a rejected
> record."

> "Every metric named by a rule must be present, finite, and correctly
> typed."

That second sentence is a test in disguise. We should add a Hypothesis
property test that generates arbitrary `VideoRecord` dicts and asserts
that if `tier != rejected` then all metrics named in the rule are
present and finite. This catches the class of bugs where a `None`
duration silently gets scored as `0.0`.

## Risks / disagreements

- SolarWM uses vision-model-in-the-loop signals (Kimi-K2.6, DOVER, VMAF,
  camera geometry). We are deliberately metadata-only in stage 1 so we
  don't have to download media just to rank a URL. Adopt the *tiered
  structure* without importing the vision-model dependency.
- Their "10 datasets" include HD-VILA-100M and Panda-70M, which live in
  YouTube-derived license territory. We do not adopt those sources; they
  are useful as *upper-bound benchmarks* for our free-source coverage.
