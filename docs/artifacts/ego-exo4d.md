# Ego-Exo4D — cooking at scale with a restrictive licence

- Paper: Grauman et al., *Ego-Exo4D: Understanding Skilled Human
  Activity from First- and Third-Person Perspectives*, IJCV 2025.
- Dataset: <https://ego-exo4d-data.org/>
- Public licence PDF (DRAFT, accepted agreement controls):
  <https://ego4d-data.org/pdfs/Ego-Exo4D-Model-License.pdf>

## What it is

A multi-view (synchronised ego + exocentric) dataset of skilled human
activity, with **cooking as the cross-cutting domain**: 678 takes, 173
participants, 60 environments, 564.13 hours of synchronised video.
Captured in 123 scenes across 13 cities worldwide. Captured on Project
Aria glasses + external cameras in a shared, gravity-aligned reference
frame.

## Why we care

This is the single best public cooking corpus for world-model work. The
reason it is *not* already in our allowlist is subtle:

- The licence is **non-transferable** and explicitly prohibits
  sublicensing. We cannot redistribute the raw clips.
- It **does** grant rights to "research, develop, train, evaluate, or
  improve any software, algorithm, machine learning model, technique,
  or technology designed to detect/classify/recognize/.../model or
  reconstruct 3D..." including for commercial use.
- It **does** grant rights to create and distribute *annotations*.

Our current `License` enum collapses this into `RESTRICTED`, which is
wrong: `RESTRICTED` in our schema means "URL-pointer only, never used
for training". Ego-Exo4D is "**training allowed, redistribution not
allowed**", a distinct tier.

## Implementation hook

- `db_structured.md` — extend the `License` enum (in a future PR) with
  a new value `TRAIN_ONLY_NO_REDISTRIBUTE`, documented as:
  "upstream explicitly permits model training but forbids
  redistribution of the raw media. `media_url` MUST be `None`;
  `url` points to the licensed download portal; `provenance` MUST
  include the per-licensee acceptance signature."
- `src/specint/records.py` — add the enum value and update
  `License.is_redistributable` to return `False` for it. Add a new
  property `License.is_training_allowed` that returns `True` for every
  redistributable license *and* for `TRAIN_ONLY_NO_REDISTRIBUTE`.
- `src/specint/quality/metrics.py` — split `_score_license` into
  `_score_training_rights` (used by default) and
  `_score_redistribution_rights` (used only for public-corpus exports).
  Today the two happen to coincide; separating them now future-proofs
  the schema.
- `src/specint/sources/ego_exo4d.py` *(future)* — a stub adapter that
  parses the public manifest, emits records with
  `license=TRAIN_ONLY_NO_REDISTRIBUTE`, and requires an environment
  variable `EGOEXO4D_LICENSE_ACCEPTED=1` to even construct. Zero
  network calls in the parser.

## Risks / disagreements

- Introducing a two-dimensional "redistribution vs training" licence
  model touches every scorer and the schema contract test. The
  adversarial judgement is that this is **worth the complexity**:
  without it, we are leaving the single highest-quality cooking corpus
  on the table.
- Still, Ego-Exo4D is **not** "internet-scale". It is 564 h. For world-
  model pretraining we need orders of magnitude more; Ego-Exo4D is a
  fine-tune / eval anchor, not a pretraining pool. Document this.
- The licence PDF is marked DRAFT FOR REVIEW. The *accepted* agreement
  (signed per licensee) governs. Our adapter must not hard-code any
  rights the DRAFT grants; it must point users to the current signed
  agreement before any ingestion step.
