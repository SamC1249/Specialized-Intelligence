# Scorer comparison — 2026-09-12

Compares baseline scorer `v1` against new scorer `v2` (adds
`procedural_density` + `language_signal`) on the shared offline
fixture set, plus the new `youtube_cc` metadata-only adapter.

## Aggregate per source

| source        | v1 records | v2 records | v1 mean_q | v2 mean_q | Δ mean_q | v1 clean | v2 clean |
| ---           | ---        | ---        | ---       | ---       | ---      | ---      | ---      |
| __total__     | 11         | 11         | 0.4930    | 0.4941    | +0.0011  | 8        | 8        |
| archive_org   | 3          | 3          | 0.3585    | 0.3834    | +0.0250  | 2        | 2        |
| common_crawl  | 1          | 1          | 0.5309    | 0.5519    | +0.0210  | 0        | 0        |
| peertube      | 2          | 2          | 0.5719    | 0.5337    | -0.0381  | 2        | 2        |
| wikimedia     | 2          | 2          | 0.6215    | 0.5510    | -0.0705  | 2        | 2        |
| youtube_cc    | 3          | 3          | 0.4766    | 0.5210    | +0.0445  | 2        | 2        |

## Clean-vs-unknown separation (defensible metric)

Mean quality of license-clean records minus mean quality of records
with `License.UNKNOWN`. Larger positive gap ⇒ scorer better ranks
usable data above unusable data at fixed K.

| scorer | mean_q (clean) | mean_q (unknown) | gap    |
| ---    | ---            | ---              | ---    |
| v1     | 0.5913         | 0.2307           | +0.361 |
| v2     | 0.5719         | 0.2864           | +0.285 |

**v1 wins this metric on the current fixtures.** v2 gives partial
credit to procedural content in records whose license we cannot
confirm, which softens the license gate. This is the tradeoff v2 was
designed to make — the goal was to discriminate **procedural** from
**non-procedural** video, not to widen the license gap further.

## Why v2 is still informative

Unit test `test_v2_dominates_v1_on_procedural_records` confirms v2
enlarges the gap between a step-by-step demonstration and a lecture
with identical license + resolution. That is the ranking dimension
that matters for cooking world models: within a batch of CC-clean
videos, we want the ones with imperative-verb-heavy transcripts to
rank higher.

## Decision

Keep **v1 as default**. Ship v2 as an opt-in scorer (`--scorer v2`)
and re-evaluate once we have real (non-fixture) data where the
procedural / non-procedural axis has meaningful spread. Both scorers
are exercised end-to-end in `tests/test_e2e_compare.py`, and every
future PR must emit both scorer reports so any regression on either
axis is caught.

## New adapter: `youtube_cc`

- Legal basis: AGENTS.md allowlist entry for the YouTube Data API v3
  restricted to `videoLicense=creativeCommon`.
- `media_url` is **always** `None`; we store URL + metadata only.
- License mapping: `creativeCommon` → `CC_BY`; anything else →
  `UNKNOWN` defensively (even if the search filter theoretically
  guarantees CC).
- Live search requires `YOUTUBE_API_KEY`; without it, `search()`
  returns `[]` so unit tests stay offline.
