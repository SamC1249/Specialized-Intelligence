# 04 — PeerTube SepiaSearch backend

**Status:** proposed (Priority-B in `plan-2026-10-12.md`).
**Hypothesis served:** H2 (yield), source-diversity.

## Problem

`PeerTubeSource` ships with a 3-instance allowlist:

```
DEFAULT_INSTANCES = (
    "https://framatube.org",
    "https://video.blender.org",
    "https://tilvids.com",
)
```

Framasoft maintains a federated meta-search at
[sepiasearch.org][sepiasearch] that indexes **1,700+** PeerTube
instances with the same `/api/v1/search/videos` surface, including
the same `licenceOneOf` filter (1 = CC-BY, 2 = CC-BY-SA,
7 = Public Domain). Reference:
[peertube-search-api-openapi.yml][openapi].

## Proposed design

- Extend `PeerTubeSource.__init__` with
  `backend: Literal["instances", "sepiasearch"] = "instances"`.
- When `backend == "sepiasearch"`, issue a single request to
  `https://sepiasearch.org/api/v1/search/videos` with
  `licenceOneOf` repeated for ids in `ALLOWED_LICENCE_IDS`.
- `parse` is unchanged — SepiaSearch returns the same
  video resource shape, so the pure parser is reusable.
- Add a `tests/fixtures/peertube/sepiasearch_cooking.json` fixture
  derived from a real SepiaSearch response (with user-identifying
  fields stripped). Assert `host` is correctly populated from the
  `account.host` field of each result rather than hardcoded to the
  calling instance.

## Risks (adversarial)

- **Single point of failure.** If SepiaSearch is down or throttling
  our IP, we lose all PeerTube yield. Keep `instances` mode as the
  default and expose `backend` as a CLI flag.
- **Instance moderation drift.** Framasoft periodically removes
  instances from the index. Yield can swing without any code change
  on our side. Record the SepiaSearch `instance` field per record so
  we can diff index membership across runs.
- **License mis-reporting at the host.** We've already seen PeerTube
  instances where `licence.id = 1` is set by default on upload
  despite the uploader attaching no license. Keep the
  `extmetadata`-style secondary signal where available (channel
  description, tags).

## Takeaway for specint

A tiny code change (one branch in `search()`) buys access to the
entire federated PeerTube graph. Zero cost. The parse path and the
license-id→enum mapping stay identical, so the risk surface is
narrow and the yield delta is measurable with the existing harness.

[sepiasearch]: https://sepiasearch.org/
[openapi]: https://raw.githubusercontent.com/api-evangelist/peertube/refs/heads/main/openapi/peertube-search-api-openapi.yml
