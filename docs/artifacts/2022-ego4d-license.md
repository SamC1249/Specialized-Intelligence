# Ego4D — License note (2022, v9 draft)

- Homepage: https://ego4d-data.org/
- License PDF: https://ego4d-data.org/pdfs/Ego4D-Licenses-Draft.pdf

## What it offers

3,670 hours of egocentric ("first-person head-cam") footage from 923
participants across 74 sites, 9 countries. Includes explicit **procedural
cooking scenarios** with step-level annotations (Goal-Step benchmark).
Superficially: exactly the kind of long-horizon, multi-object,
irreversible-state footage our project targets.

## Legality under our constraints

**Not in the allowlist today.** Access requires an individually-signed
non-exclusive, non-transferable license per licensee, with a 14-day AWS
credential window and renewal ritual. The license *does* permit
commercial ML training under Purpose §2, but:

1. The agreement is **not a public license** (no CC / no OSI-style
   permission grant). Our AGENTS.md hard constraint #1 says
   "permissively-licensed... or explicitly-allowed public APIs".
   Per-user contracts don't cleanly qualify.
2. Redistribution is limited to publications and companion websites
   (Purpose §1). Distributing frames as training data to a downstream
   model consumer is at best ambiguous.
3. Credentials expire; provenance would need to record the specific
   accepted-agreement version, not just the URL.

## Ideas we adopt

1. **Goal-Step schema.** Ego4D's action segmentation labels ("goal",
   "step", "substep") are a good structural template for the
   `recipe_steps: list[str]` field in our `VideoRecord`. Consider a
   future field `step_start_s: float | None` if we ever aligned video
   to steps.
2. **Multi-site diversity as a quality axis.** Ego4D publishes per-site
   distribution. Our comparison harness should eventually publish
   `unique_authors`-style geographic diversity when license-clean
   sources let us (Commons `Coord` field, PeerTube `originallyPublishedAt`).

## Follow-up

If we ever *do* add Ego4D, it belongs in a new source class marked
`requires_signed_agreement=True`, with the extractor refusing to run
unless `SPECINT_EGO4D_AGREEMENT_ID` is set. Do **not** enable by default.
