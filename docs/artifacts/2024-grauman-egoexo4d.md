# Ego-Exo4D (Grauman et al., IJCV 2025)

- Paper: https://link.springer.com/article/10.1007/s11263-025-02557-6
- Project: https://ego-exo4d-data.org/

## Claim

1,286 hours of *simultaneously-captured egocentric and exocentric*
video of skilled activities (sports, cooking, music, dance, bike
repair) across 740 participants in 13 cities. Multi-modal: audio, eye
gaze, 3D point clouds, camera poses, IMU. Language layers include
"expert commentary" (a coach describing what the participant is doing
well/badly), first-person "narrate-and-act" tutorials, and single-
sentence atomic action descriptions.

## Evidence

- Benchmark suite covers proficiency estimation, keystep recognition,
  cross-view translation, 3D hand/body pose — non-trivial tasks that
  demand more than YouTube-scale weak supervision.
- Ego4D predecessor: 3,670 hours of unscripted daily life across 9
  countries.
- **License gate.** Both datasets require an EULA signed by the
  requesting institution. Redistribution is forbidden; models trained
  on them can be released but the raw video cannot.

## Steal

1. **Multi-view is the frontier signal.** For world modeling, an
   ego+exo pair of the same recipe is >> the sum of two independent
   videos. Design implication: our `VideoRecord` schema should already
   allow *grouping* multiple records that share a `recording_group_id`
   or a `sibling_records: list[str]` field. **Not urgent** but note as
   an eventual schema evolution.
2. **Expert commentary as a supervision signal.** On our permissively
   licensed sources this maps to blog post text alongside a Wikibooks
   Cookbook video — worth chasing as a separate text stream field.
3. **Language layers reveal quality gradations.** Their three-tier
   language annotation (atomic → tutorial → expert) is a template for
   a `text_layers: dict[str, str]` field we could add to VideoRecord
   later. Skip today.

## Implications for specint

- Confirms our narrow choice of *cooking* as a first target — it
  overlaps with Ego-Exo4D domains, so a permissively-licensed cooking
  corpus is a defensible complement, not a duplicate, of Ego-Exo4D.
- **Do not attempt to redistribute** Ego-Exo4D clips even under
  research fair use. Treat as *comparison-only* — we can measure our
  quality score distribution against a small sample once someone on
  the team has signed their EULA and can hold the data on a private
  disk. This does *not* enter the CI pipeline.
- Schema future-work: add `sibling_records`, `recording_group_id`
  fields (deferred, but documented here so we don't paint ourselves
  into a corner with a flat schema).
