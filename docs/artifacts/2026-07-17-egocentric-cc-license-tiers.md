# CC-BY-NC egocentric video: the license tier we are currently discarding

## Datasets in scope

| Dataset                | Domain                      | Scale         | License      | Notes                                                        |
| ---------------------- | --------------------------- | ------------- | ------------ | ------------------------------------------------------------ |
| EPIC-KITCHENS-100      | Egocentric kitchen actions  | 100 h, 45 kitchens | CC-BY-NC 4.0 | Multi-day, unscripted, 20 M frames. Bristol.                 |
| EPIC-KITCHENS HD-EPIC  | Extended EPIC-KITCHENS      | 30 h dense annotations | CC-BY-NC 4.0 | CVPR 2025 paper.                                             |
| Ego4D                  | Egocentric daily life       | 3,670 h, 9 countries | CC-BY-NC 4.0 (requires signed license agreement) | Includes cooking segments.                                   |
| Ego-Exo4D              | Skilled activities, ego+exo | 1,286 h       | CC-BY-NC 4.0 | Cooking is one of eight skill domains.                       |
| EPFL-Smart-Kitchen-30  | 9-camera + IMU + HoloLens 2 | 29.7 h, 16 subjects, 4 recipes | CC-BY-NC 4.0 | Zenodo 15551913 / 15535461. Extremely dense (33.78 actions/min). |
| Mali food-and-beverage | Documentary food prep       | 5+ videos     | **CC-BY 4.0** | Deep Blue Data, U Michigan; NSF DEL program. Unusually one of the few CC-BY (commercial-ok) options. |

## Why our current pipeline throws all of this away

`records.License.is_redistributable` returns False for anything not
in `{CC0, CC-BY, CC-BY-SA, PD, OTHER_FREE}`, and any candidate
license we don't recognize collapses to `UNKNOWN`. So today, when a
NARA record fails classification or a NC dataset is registered, both
end up in the same bucket ("do not train"). That is correct for
commercial pretraining. It is *catastrophically over-conservative*
for research-only ablations, which is where the highest-density
procedural cooking data actually lives.

## Proposal — use-case-aware license tiers

Extend `License`:

```
CC_BY_NC       = "CC-BY-NC"
CC_BY_NC_SA    = "CC-BY-NC-SA"
CC_BY_ND       = "CC-BY-ND"
CC_BY_NC_ND    = "CC-BY-NC-ND"
```

Add:

```python
class License(str, Enum):
    def permits(self, use_case: Literal["research", "commercial"]) -> bool:
        if use_case == "commercial":
            return self.is_redistributable  # unchanged commercial-safe set
        if use_case == "research":
            return self in {
                License.CC0, License.CC_BY, License.CC_BY_SA,
                License.PUBLIC_DOMAIN, License.OTHER_FREE,
                License.CC_BY_NC, License.CC_BY_NC_SA,
                License.CC_BY_ND, License.CC_BY_NC_ND,
            }
        return False
```

Then `compare/harness.py` accepts a `use_case` and routes
`n_license_clean` through `License.permits(use_case)`. The default
remains `commercial` so nothing regresses silently.

## Legal caveats we must document

- CC-BY-NC-* does **not** authorize a model whose weights will be
  used for commercial inference. Even research-only pretraining is
  a gray area if the resulting weights are ever released publicly
  (see the ongoing NYT-v-OpenAI arguments about "downstream
  commerciality"). Treat `--use-case research` as: **this checkpoint
  is a diagnostic artifact and shall not be released or served for
  commercial inference.**
- Ego4D requires an executed license agreement per participant. Do
  not distribute the raw videos through this repo. Metadata-only
  index is fine.
- Attribution obligations under CC-BY-NC-* are non-negotiable. Our
  `VideoRecord.author` is already `Optional`; make it *required* for
  any record with a NC/BY license, or fail ingestion.

## Concrete deliverable pointer

Maps to plan 2026-07-17 deliverable 2 (H9). See H9's success
criterion: "a `--use-case commercial` compare drops NC hours to
zero" is the regression test.

## Falsifier

If, after adding the `permits(use_case)` API, running
`python -m specint compare --fixtures --use-case commercial` on a
fixture containing a NC record does not drop `n_license_clean` by
exactly the NC record's count, the routing is wrong. This is the
observability regression test that should ship *with* the license
change, not after it.
