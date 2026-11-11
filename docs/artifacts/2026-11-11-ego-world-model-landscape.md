# Artifact — Egocentric / world-model video dataset landscape (commercial-use readout)

**Access date:** 2026-11-11.
**Primary source:** Fourthuman, *Egocentric Video Datasets* (read
2026-10-30), cross-referenced with each dataset's own license page.

## Dataset license readout

| Dataset | Scale | License | Commercial training? |
| --- | --- | --- | --- |
| **Ego4D** | 3,670 h / 931 wearers | Ego4D licence agreement | Listed uses only; **footage may not be redistributed**. |
| **Ego-Exo4D** | 1,286 h (ego + exo views) | Ego-Exo4D agreement | Commercial use documented, but signed on request. |
| **EPIC-KITCHENS-100** | 100 h / 700 vids | CC BY-NC 4.0 | **No** (commercial via email). |
| **EgoDex** | 829 h, 3D hand tracking | CC BY-NC-ND | **No.** |
| **HOI4D** | 2.4M RGB-D frames | CC BY-NC 4.0 | **No.** |
| **HoloAssist** | 166 h, instructor-performer pairs | **CDLA-Permissive-2.0** | **Yes.** |
| **Assembly101** | 4,321 vids, 4 ego views | CC BY-NC 4.0 | **No.** |
| **Aria Everyday Activities** | 143 activity seqs | AEA agreement | Non-commercial research only. |
| **Nymeria** | 300 h, full-body motion + language | CC BY-NC 4.0 | **No.** |
| **HOT3D** | 833+ min | CC BY-SA footage / CC BY-NC-SA labels | Footage yes, labels no. |
| **Ego-1K** | 956 clips / 2.3 h | FAIR Noncommercial | **No.** |
| **Egocentric-10K** | 10,000 h, factory-floor manipulation | **Apache-2.0 (after HF gate)** | **Yes.** |
| **NVIDIA SDG-SynHuman** | 236,937 synthetic clips / 5,841 h | **OpenMDW 1.1** (synthetic, commercial OK) | **Yes.** |
| **TrainThemAI POV ADL sample** | 26 clips / ~27 GB | **MIT** | **Yes (sample only).** |
| **1X worldmodel_raw_data** | sharded, humanoid state+video | CC BY-NC-SA 4.0 | **No.** |
| **PKU Open-Sora-Dataset** | 274 h (mixkit+pexels+pixabay) | CC0 | **Yes.** |

## Takeaways

1. **Commercial-use, permissive, procedural, long-horizon video at
   >100 hours is *extremely rare*.** The only candidates in the
   table are HoloAssist (166 h), Egocentric-10K (10,000 h,
   factory), SDG-SynHuman (5,841 h synthetic), and PKU Open-Sora
   (274 h, mostly B-roll, not procedural).
2. **Cooking-specific, commercial, permissive, procedural, >100 h
   does not appear to exist off-the-shelf.** EPIC-KITCHENS,
   Assembly101-food, HOI4D-kitchen are all NC. This validates the
   entire Specialized-Intelligence thesis: the commercial-use
   procedural-cooking corpus has to be *assembled* from permissive
   sources, not *bought* or *downloaded wholesale*.
3. **Synthetic is a legitimate escape hatch.** SDG-SynHuman shows
   a viable path when real permissive data runs out. We should add
   a `source="synthetic"` enum value and a `blender_physics`-style
   adapter placeholder in a future plan, so our benchmark harness
   can compare real vs synthetic yield on the same quality axes.
4. **HoloAssist methodology is worth copying.** Instructor-performer
   pairs are an unusually high density of procedural supervision.
   We cannot replicate that on the open web, but we can up-weight
   recipe pages that include multi-camera or paired videos (the
   `schema.org/VideoObject` `isPartOf` property points at this).

## Implementable takeaways for `Coding-Agent`

- Extend the comparison harness report with a **"comparable
  external dataset"** column that cites the nearest permissive
  dataset by scale for each `domain`. This is documentation, not
  code — but it anchors our yield numbers to the broader
  landscape.
- Add `License.CDLA_PERMISSIVE` and `License.OPENMDW` to the
  taxonomy (both qualify as `is_redistributable=True`). Update
  `db_structured.md` and ship a migration-style test.
- Explicitly *do not* ingest any of the CC-BY-NC datasets above —
  not even metadata-only — because our records flowing through the
  compare harness end up in a public report. A hostile reader
  could argue that even indexing them implies training use.
  Document this in `AGENTS.md`'s allowlist section.
