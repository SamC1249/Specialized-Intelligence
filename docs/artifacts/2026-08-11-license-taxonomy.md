# License taxonomy — canonical strings and known adversarial cases

Date: 2026-08-11  ·  Author: Adversarial-Agent

Our `License` enum is small (`CC0`, `CC_BY`, `CC_BY_SA`,
`PUBLIC_DOMAIN`, `OTHER_FREE`, `UNKNOWN`, `RESTRICTED`). The mapping
from upstream strings/ids to the enum is where mistakes turn into
license violations. This note enumerates the strings we must correctly
classify and the traps a naive regex would fall into.

## Wikimedia Commons — `extmetadata.LicenseShortName`

Real-world values (from Commons API, spot-checked 2026-08-11):

| Upstream string | Correct enum | Trap |
| --- | --- | --- |
| `CC0` | `CC0` | Substring match must be case-insensitive. |
| `CC BY 4.0`, `CC-BY-4.0`, `Attribution` | `CC_BY` | `Attribution` alone can be mis-tokenised to CC-BY when it's actually CC-BY-NC. |
| `CC BY-SA 4.0`, `CC-BY-SA-3.0`, `Attribution-ShareAlike` | `CC_BY_SA` | Ordering: check `BY-SA` before `BY`. |
| `Public domain`, `PD-US`, `PD-old-100` | `PUBLIC_DOMAIN` | `PD-shape` and `PD-textlogo` are US-copyright-shape assertions, still `PUBLIC_DOMAIN` for our purposes. |
| `CC BY-NC-SA 4.0`, `Attribution-NonCommercial-ShareAlike` | `RESTRICTED` | Trap: naive check for `BY-SA` matches this. Must reject anything containing `NC` first. |
| `CC BY-ND`, `CC BY-NC-ND` | `RESTRICTED` | ND = no derivatives; excluded regardless of NC. |
| `GFDL`, `GFDL-1.2` | `OTHER_FREE` | Widely used pre-2009 on Commons; GFDL is free but incompatible with pure-CC pipelines. |
| Multi-license: `CC-BY-SA-4.0 OR GFDL` | `CC_BY_SA` | Pick the most permissive share-alike-compatible label; do not silently downgrade to `UNKNOWN`. |
| Empty / missing | `UNKNOWN` | Never `RESTRICTED` by default. |

Current bug hypothesis (H3 in `plan-2026-08-11.md`): the wikimedia
`_coerce_license` does the `BY-NC` check before the `CC-BY` check,
which is correct, but does **not** check for `-ND-` in combination
with just `CC-BY` (only in combination with `BY-NC`). A record
labelled `CC BY-ND 4.0` today falls through to `CC_BY`. Test matrix
required.

## Internet Archive — `licenseurl`

`archive.org` `licenseurl` values are canonical Creative Commons URLs.

| Upstream URL | Correct enum |
| --- | --- |
| `http://creativecommons.org/publicdomain/zero/1.0/` | `CC0` |
| `http://creativecommons.org/licenses/by/3.0/` | `CC_BY` |
| `http://creativecommons.org/licenses/by-sa/4.0/` | `CC_BY_SA` |
| `http://creativecommons.org/licenses/by-nc/4.0/` | `RESTRICTED` |
| `http://creativecommons.org/licenses/by-nc-sa/3.0/` | `RESTRICTED` |
| `http://creativecommons.org/licenses/by-nd/4.0/` | `RESTRICTED` |
| `http://creativecommons.org/publicdomain/mark/1.0/` | `PUBLIC_DOMAIN` |
| missing / empty | `UNKNOWN` |

Current adapter uses substring matching. Note that
`"/by/"` is *inside* `"/by-nc/"` at some URL shapes if we're careless.
Existing implementation checks `by-nc` first, which is fine; keep
that ordering invariant with a test.

## PeerTube — numeric `licence.id`

| id | Meaning | Enum |
| --- | --- | --- |
| 1 | Attribution (CC-BY) | `CC_BY` |
| 2 | Attribution-ShareAlike (CC-BY-SA) | `CC_BY_SA` |
| 3 | Attribution-NoDerivatives | `RESTRICTED` |
| 4 | Attribution-NonCommercial | `RESTRICTED` |
| 5 | Attribution-NonCommercial-ShareAlike | `RESTRICTED` |
| 6 | Attribution-NonCommercial-NoDerivatives | `RESTRICTED` |
| 7 | Public Domain Dedication (CC0) | `CC0` |

Current adapter drops ids 3–6. Adding an assertion for
`ALLOWED_LICENCE_IDS ⊂ {1,2,7}` in a unit test prevents accidental
widening.

## YouTube — API `videoLicense`

Only two values are relevant to us:

- `youtube` → default restrictive → `License.RESTRICTED`.
- `creativeCommon` → maps to `License.CC_BY` (YouTube's CC-BY is CC-BY
  4.0 per Google's help centre), BUT re-verification against the watch
  page is required because uploaders can mis-tag content.

## Openverse (image/audio, not video)

We considered Openverse for video; **its native API does not support
videos** — video is delegated to "external sources" (Vimeo, Wikimedia,
YouTube CC filter). So Openverse is only relevant later for image/audio
augmentation and is out of scope for `sources/`.

## Implications for specint

- **Add** `tests/test_license_taxonomy.py` (P0 for Coding-Agent) that
  parameterises each row of the tables above against the relevant
  `_coerce_license` / `_license_from_url` function. This is the
  cheapest way to close H3.
- **Refactor** the per-source license coercers into a shared
  `src/specint/licensing.py` so the same string maps to the same enum
  regardless of upstream — today each adapter has its own logic.
- **Emit `RESTRICTED` explicitly** whenever we successfully identified
  a non-redistributable license, so downstream telemetry
  distinguishes "we know it's blocked" from "we don't know".
