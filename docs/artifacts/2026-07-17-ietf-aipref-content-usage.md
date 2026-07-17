# IETF AIPREF — Content-Usage header & robots.txt rule

- `draft-ietf-aipref-attach-04` (28 Oct 2025) — defines the HTTP
  `Content-Usage` header field and the `Content-Usage` directive for
  `robots.txt`. Updates RFC 9309. Intended status: Proposed Standard.
- `draft-ietf-aipref-vocab-04` (Apr 2026) — defines the vocabulary:
  categories `train-ai` and `search`, values `y` (allow) and `n`
  (disallow). Expiry Oct 2026.
- Working-group milestone: submit a standards-track spec to the IESG
  by **August 2026**. Attach draft revision -04 has technically
  lapsed under the 6-month rule (as of May 2026) but no newer
  revision has replaced it — status is "active WG document,
  pre-standard."

## What we must implement

### Header parser

`Content-Usage` is a Structured Field Dictionary (RFC 8941). Example:

```
Content-Usage: train-ai=n, search=y
```

Minimum viable parser:

- Split on commas outside quoted strings.
- For each item, split on `=` into `(category, value)`.
- Trim whitespace, lowercase both sides.
- Reject any category not in the AIPREF vocabulary
  (`{"train-ai", "search"}` per `-vocab-04`; the vocab is designed
  to grow, so log-and-drop rather than raise on unknown categories).

### `robots.txt` rule

Per `-attach-04` §3, the rule appears in the standard robots.txt
group syntax:

```
User-Agent: *
Allow: /
Content-Usage: train-ai=n
```

Semantics: the preference attaches to any resource that the group
covers via its `Allow` / `Disallow` rules.

### Enforcement rule for our pipeline

- For any candidate record whose upstream page emits `train-ai=n`
  (either as a `Content-Usage` HTTP header, a `<meta http-equiv=
  content-usage>` tag, or a `robots.txt Content-Usage: train-ai=n`
  rule covering the URL), demote the record's `License` to
  `RESTRICTED`.
- Do this **before** license classification. AIPREF overrides
  even a CC-BY declaration, because CC-BY *did not exist* as an
  informed consent to AI training; the AIPREF signal is the
  publisher's explicit AI-time preference.
- Record the demotion in `Provenance.query` (append
  `;aipref=train-ai=n`) so the audit is discoverable in the report.

## What we do *not* do

- Do not enforce `search=n`. We are training-data collection, not
  a search index; `search=n` is orthogonal.
- Do not distinguish "no preference expressed" from `train-ai=y`.
  Absent is *not* consent under the draft's semantics for existing
  content; we conservatively treat absent preference as
  license-driven (default to whatever the CC / PD declaration says).
- Do not implement the newer individual drafts
  (`content-bound-consumption`, `real-time-bindings`) — not adopted
  by the WG yet.

## Interoperability notes

- The Common Crawl WARC captures include HTTP response headers in
  the `WARC-Type: response` records under `HTTP/1.1 200 OK` blocks.
  Our current adapter parses only the HTML body; a small extension
  to also expose the header block is required (Coding-Agent).
- `robots.txt` for a host is captured in Common Crawl as its own
  URL. We can pre-load it per host from a checked-in fixture for
  offline tests.

## Concrete deliverable pointer

Maps to plan 2026-07-17 deliverable 4 (H7): `quality/aipref.py` with
`parse_content_usage()` and `has_train_ai_optout()`, wired into
`sources/common_crawl.py` and validated by a fixture pair.

## Falsifier

If, on the extended Common Crawl fixture pair, the opt-out page is
*not* demoted to `RESTRICTED` after Coding-Agent lands the parser, the
implementation is wrong; the fixture is deliberately shaped so that
the CC-BY-tagged page with `train-ai=n` must fail its previous
license-clean status.
