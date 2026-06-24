# PeerTube — Federated, license-strict crawl recipe

> Source: PeerTube REST API docs
> (<https://docs.joinpeertube.org/api-rest-reference.html>),
> `dltHub` PeerTube source connector, JoinPeerTube instance whitelist.
> Notes captured: 2026-06-24 by Adversarial-Agent.

## Why PeerTube

- **Federated and ToS-friendly.** Each instance hosts its own videos under
  its own ToS, but the *protocol* (ActivityPub + a documented REST API)
  is explicitly designed for federated reading. There is no anti-bot
  protection layer to circumvent; a polite client just needs a
  `User-Agent`.
- **Per-video license metadata.** PeerTube exposes `license` on every
  video. The enum maps cleanly to SPDX: CC-BY-4.0, CC-BY-SA-4.0,
  CC-BY-ND, CC-BY-NC, CC0, public domain, "default" (uploader-chosen).
- **Cross-instance routing.** `@user@instance` resolves federated
  identities; the API at `https://<instance>/api/v1/videos?search=…`
  supports searching the local index, and `?include=` returns federated
  results. We can index e.g. framatube.org, video.blender.org,
  tilvids.com, makertube.net, peertube.cpy.re.

## License posture

PeerTube licenses are encoded as integers (1=CC-BY, 2=CC-BY-SA, etc.) in
the API response. The `license_check` step *must* refuse anything we
cannot map to an SPDX identifier with high confidence.

A naive crawl will silently include `license = null` videos. Our adapter
must **default to `excluded=true` with reason `license_missing`** rather
than `license=UNKNOWN`.

## Concrete recipe (planned for v1 implementation)

```
discover(peertube)
  for instance in JOINPEERTUBE_WHITELIST:
    page = 0
    while True:
      r = GET https://{instance}/api/v1/videos
            ?count=100&start={page*100}
            &filter=local
            &languageOneOf=…
            &tagsOneOf=cooking,recipe,kitchen,food
            &sort=-publishedAt
      if r is empty: break
      for v in r["data"]:
        yield row_from_peertube(v, instance)
      page += 1
```

Per-row fields we keep:

- `canonical_url`   = `https://{instance}/videos/watch/{v.uuid}`
- `media_url`       = `v.files[0].fileUrl` (only set if license is open)
- `source`          = `peertube_cc_by` / `peertube_cc_by_sa` / `peertube_cc0`
- `license`         = SPDX-mapped from `v.licence.id`
- `attribution`     = `v.account.displayName @ v.channel.host`
- `duration_s`      = `v.duration`
- `language`        = `v.language.id`  (BCP-47)
- `tags`            = `v.tags ∪ {"cooking"}`
- `pipeline_version`= "0.0.2"

## Adversarial concerns

1. **Federation-of-trust.** A malicious instance can lie about license
   metadata. Mitigation: cap per-instance contribution, require a
   `license_confidence` field, and re-verify via `Content-License`
   HTTP header or the page's HTML metadata when possible.
2. **NSFW co-mingling.** The `nsfw` flag is present but uploader-set.
   Default to `nsfw=false` only.
3. **Per-instance ToS drift.** The instance's local ToS may *narrow* the
   federation license. Adapter should fetch `/about` once per instance
   and refuse any instance whose ToS is not auto-classifiable as
   "redistribute-OK for CC content."
4. **Low cooking-domain volume.** Realistic estimate: hundreds, not
   thousands, of cooking-tagged videos federation-wide. PeerTube is a
   *substitute for YouTube CC search*, not a replacement for the
   long-tail web. Use it for diversity and license-cleanliness, not
   bulk.

## Action items

1. New `components/sources/peertube.py` adapter (planned). Stubs and
   fixtures-only tests first; live network only behind an opt-in env
   var, never in CI.
2. JoinPeerTube whitelist as a checked-in JSON file
   (`components/sources/peertube_whitelist.json`), updated quarterly.
3. Pre-commit hook (planned): forbid any source adapter that doesn't
   emit `license_confidence`.

## Key references

- PeerTube API: <https://docs.joinpeertube.org/api-rest-reference.html>
- JoinPeerTube instance list:
  <https://joinpeertube.org/instances#instances-list>
- dltHub PeerTube source connector docs.
