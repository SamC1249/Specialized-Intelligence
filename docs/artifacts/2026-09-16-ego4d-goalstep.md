# Ego4D + Ego4D Goal-Step

- **Ego4D** — Grauman et al. CVPR 2022.
  [arXiv:2110.07058](https://arxiv.org/abs/2110.07058) ·
  [project](https://ego4d-data.org/).
- **Ego4D Goal-Step** — Song, Byrne, Nagarajan, Wang, Martin, Torresani.
  NeurIPS 2023 D&B.
  [paper (PDF)](https://papers.neurips.cc/paper_files/paper/2023/file/7a65606fa1a6849450550325832036e5-Paper-Datasets_and_Benchmarks.pdf).

## What they built

Ego4D is **3,670 hours** of egocentric video from **931 unique camera
wearers, 74 locations, 9 countries** — the current reference corpus for
"long-form, unscripted, hand-object-interaction" video. Ego4D Goal-Step
adds a **hierarchical goal → step → substep taxonomy** on top: 2,807
hours labelled with 319 goals (34 scenarios), and a dense **48k step
segments (430 hours)** focused on cooking.

## What we can steal

- **Hierarchical schema.** Our `VideoRecord.recipe_steps` is a flat
  string list; a video training corpus for world models wants
  *(goal, step, substep, start_s, end_s)* tuples. This is a schema
  evolution we should stage now so downstream annotation tools (LLM +
  narration alignment) don't have to redesign later.
- **Diversity accounting by scenario × geography × camera-wearer.**
  Ego4D's ethics + diversity story is what a serious data provenance
  audit looks like. We should add optional `record.geo` (country) and
  `record.author_hash` (stable hash of `author`) to the schema, and
  emit them in `BenchmarkResult` as `unique_geographies` and
  `unique_author_hashes`. This defends against the mode-collapse
  failure where a "large" corpus is 90% one uploader.
- **Cooking-first framing is not narrow.** Ego4D Goal-Step chose
  cooking for the same reason we did: densest procedural supervision
  per hour. Their taxonomy — 86 cooking goals × 514 fine-grained steps
  — is a useful upper-bound to compare our discovered taxonomy against
  once we have one.

## What we must *not* copy

- Ego4D is under a **custom license (Ego4D License Agreement)** that
  restricts commercial use and requires per-user agreement. It is
  **not** on our allowlist. We can cite the paper for methodology; we
  cannot mirror the videos or annotations.
- Their collection required paid participants with cameras. Our mandate
  is *internet-scale, no-money-spent*. Egocentric footage on the open
  web is much sparser; we should flag it as an explicit gap rather
  than pretend our recipe-blog videos are equivalent.

## Implementation hooks

- `db_structured.md` and `src/specint/records.py` → add optional
  `geo_country: str | None`, `author_hash: str | None`, and a
  `Segment` sub-model list `segments: list[Segment] = []` with
  `(start_s, end_s, label, level)` — nullable, backwards compatible.
- `src/specint/compare/harness.py` → new `BenchmarkResult` fields
  `unique_geographies`, `unique_author_hashes` (with `hashlib.blake2b`,
  16-byte digest, unsalted for cross-source join-ability).
- `src/specint/sources/` → have each adapter populate `geo_country`
  when the upstream gives it (Commons: `Country` extmetadata;
  Archive.org: sometimes in `subject`; PeerTube: per-instance).
