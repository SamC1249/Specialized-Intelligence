# docs/artifacts

Short notes on external work that has shaped — or should shape — the
Specialized-Intelligence pipeline. Every artifact must answer three
questions in ≤ ~400 lines:

1. **Claim.** What does the source assert?
2. **Evidence.** How well is that backed?
3. **Steal.** What concrete, legal thing do we adopt into our pipeline,
   and against which deliverable in the latest `docs/plan-*.md`?

Naming: `YYYY-source-slug.md` (e.g. `2019-miech-howto100m.md`).
Add new artifacts by writing a new file and referencing it from the
active plan under a `[x] docs/artifacts/... digested` checkbox.

## Current artifacts

| File                                    | One-line summary                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `2019-miech-howto100m.md`               | 1.2M YouTube "how to" videos; ontology from WikiHow → 23k visual tasks. Ontology, not media.     |
| `2024-grauman-egoexo4d.md`              | 1,286 h of synchronized ego+exo footage of skilled activities; multi-modal, license-gated.       |
| `2007-manku-simhash.md`                 | 64-bit SimHash + k-bit-difference index → web-scale near-duplicate detection at 8B docs.         |
| `2024-c2pa-content-credentials.md`      | Cryptographic manifests that carry `cawg.training-mining` opt-in/out we must honour.             |
| `2018-zhou-youcook2.md`                 | 2k cooking videos, 89 recipes, temporal step boundaries. Gold reference for procedural density.  |

## How this ties to the plan

Each note ends with an "Implications for specint" section that names the
plan checkbox it feeds. If a note doesn't map to a checkbox, the
Adversarial-Agent should file a new one on the next daily plan or
delete the artifact.
