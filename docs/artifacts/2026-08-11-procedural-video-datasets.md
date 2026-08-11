# Procedural / cooking video research datasets — through the license lens

Date: 2026-08-11  ·  Author: Adversarial-Agent

We are trying to *not* rebuild what academia has already released. But
we are also constrained to legally redistributable data, which
eliminates several otherwise-obvious references. This note maps the
main procedural-video corpora against our hard constraint #1 in
`AGENTS.md`.

## Landscape

| Dataset | Hours | Domain | License (declared) | Legal for us? |
| --- | --- | --- | --- | --- |
| Ego4D | ~3,700 | Egocentric daily-life (incl. cooking) | MIT (annotations) + custom EULA for video | Mixed: annotations yes, videos require EULA click-through — **not fully open**, but MIT-annotations are usable as *labels* on our own corpus. |
| EPIC-KITCHENS-100 | 100 | Egocentric cooking (45 kitchens) | **CC-BY-NC 4.0** | **NO.** Non-commercial excludes frontier model training. |
| HD-EPIC (2025) | 41 | Egocentric cooking + digital twins | **CC-BY-NC 4.0** | **NO.** Same clause as EPIC-KITCHENS. |
| HowTo100M | ~15,000 (nominal) | Instructional (YouTube) | Not explicitly declared; underlying YouTube licenses vary | **Do not treat as free.** Only the subset with `videoLicense=creativeCommon` on YouTube is safe, and even then metadata-only. |
| YouCook2 | 176 | Cooking (YouTube) | Not redistributed as video; annotations only | Annotations may be usable; media itself must come from CC subset. |
| COIN | 476 | Instructional | Video not redistributed; annotations CC-BY-NC-SA | Annotations off-limits (NC clause); framework insight only. |

Source: dataset landing pages, EPIC-KITCHENS 2024/2025/2026 pages
(`epic-kitchens.github.io/2024`, `.../2026`, `hd-epic.github.io/site`),
Ego4D announcement.

## Key takeaways for specint

- **The single most-cited cooking dataset in the literature is off
  limits for us.** Any comparison to EPIC-KITCHENS numbers must be
  explicitly marked as "for orientation only, not a corpus we can
  redistribute."
- **Ego4D's MIT-licensed annotations are the most usable slice.** They
  are a legitimate source of taxonomies (verbs, nouns, action
  segmentations) that we can adopt without laundering NC-only data.
- **HowTo100M's URL list is a legitimate starting point** only if we
  re-filter each video against YouTube's `videoLicense=creativeCommon`
  flag at fetch time. Do not trust the paper's implicit assumption
  that everything is fair game.

## Ideas to steal (that don't leak NC data)

1. **Verb/noun taxonomy from Ego4D-MIT** — reuse as a schema for
   `keywords` on cooking `VideoRecord`s. Enables cross-source
   comparison of "which sources cover which action types?".
2. **Pause-and-Talk narration protocol** from EPIC-KITCHENS — cite in
   plan as the standard way to align text with actions; when we later
   build a captioning quality metric, this is the reference protocol
   without requiring their footage.
3. **Digital-twin idea from HD-EPIC** — establishes that per-scene
   3D reconstruction pairs well with cooking video for world models.
   We won't build 3D twins from scratch, but this justifies preferring
   videos with static camera + long duration in `quality/metrics.py`.

## Implications for specint

- **Add** an explicit `license_family: {"cc0","cc-by","cc-by-sa","pd",
  "other_free"}` restriction check in the aggregation harness so a
  future contributor cannot silently sneak an `NC` dataset in.
- **Reject** any proposal that suggests importing EPIC-KITCHENS or
  HD-EPIC video assets, no matter how they are re-hosted.
- **Add** an artefact-level note on Ego4D annotations as a possible
  taxonomy import in a later plan; treat as a "yes with process"
  rather than an automatic import.

## References

- EPIC-KITCHENS project: `https://epic-kitchens.github.io/`
- HD-EPIC (CVPR 2025): `https://hd-epic.github.io/site/`
- Ego4D paper: `https://ego4d-data.org/`
- HowTo100M (Miech et al., 2019):
  `https://www.di.ens.fr/willow/research/howto100m/`
- YouCook2: `http://youcook2.eecs.umich.edu/`
- COIN: `https://coin-dataset.github.io/`
