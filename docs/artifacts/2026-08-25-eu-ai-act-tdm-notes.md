# EU AI Act TDM opt-out — implementation cheat-sheet

Author: Coding-Agent · Date: 2026-08-25

## What the Act asks of us

The EU AI Act (Regulation (EU) 2024/1689) obliges providers of
general-purpose AI models to comply, in the Union, with the copyright
Text-and-Data-Mining opt-outs set out in Directive (EU) 2019/790
Article 4. The GPAI Code of Practice (final version, adopted July 2026,
enforceable 2 August 2026) makes three signals authoritative:

1. **`robots.txt`** for the crawling stage.
2. **TDMRep** — `/.well-known/tdmrep.json` and the `TDM-Reservation`
   HTTP response header — for the *reservation* stage.
3. **AI-specific opt-out lists** — e.g. `ai.txt` — where site operators
   express model-training preferences separately from generic crawling.

`ai.txt` is the industry convention (Spawning). It is not mandated by
the Act but the Code of Practice treats it as evidence of "appropriate
technical protection measures".

## How this repo captures the signals

Every fetch goes through `specint.compliance.rights`:

| Signal            | Silence means | Reserved means | Where we store it |
| ----------------- | ------------- | -------------- | ----------------- |
| `robots.txt`      | allowed       | disallowed     | `RightsSignal.robots_allowed: bool` |
| `tdmrep.json`     | allowed (`ABSENT`) | disallowed (`RESERVED`) | `RightsSignal.tdmrep: TdmStatus` |
| `TDM-Reservation` header | allowed | disallowed | folded into `tdmrep` |
| `ai.txt`          | *unknown*     | disallowed     | `RightsSignal.ai_txt: dict` |

`RightsSignal.is_permitted` returns `True` iff every present signal
permits crawling; a `None` signal defaults to *not permitted*
(fail-closed).

## Fixture-driven parser tests

`tests/fixtures/rights/` ships one file per allowlisted source:

- `robots_wikimedia.txt` — specint carve-out vs wildcard block
- `robots_archive_org.txt` — allowlist by path
- `robots_peertube.txt` — permissive default
- `robots_youtube.txt` — hard wildcard block with specint carve-out
- `robots_common_crawl.txt` — silence
- `tdmrep_reserved.json`, `tdmrep_allowed.json` — path-specificity cases
- `ai.txt` — wildcard block + specint allow + gptbot deny

`tests/test_compliance.py` exercises the longest-match, silence-semantics,
and permission-matrix branches offline.

## Open follow-ups

- The `raw_sha256` of the *rights payload* itself should be hashed and
  co-signed with the record; today we only hash the upstream search
  response body.
- We do not yet cache `RightsSignal`s per host with a TTL — a
  `rights/{host}.json` on-disk cache is a follow-up to keep the live
  fetcher polite.
- C2PA-style signed manifests (see `2026-08-25-c2pa-notes.md`) will
  supersede the ad-hoc `raw_sha256` + `extractor_git` pair once we
  have a key management story.
