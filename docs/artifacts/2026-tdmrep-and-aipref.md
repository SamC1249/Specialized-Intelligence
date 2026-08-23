# TDMRep, IETF AIPREF, IPTC opt-out signals — what a lawful crawler must honour

- **W3C TDM Reservation Protocol (TDMRep)** — Final Community Group
  Report, 10 May 2024.
  <https://www.w3.org/community/reports/tdmrep/CG-FINAL-tdmrep-20240510/>
- **IETF AIPREF WG** — chartered Jan 2025; I-Ds define a `Content-Usage`
  vocabulary attachable via robots.txt or HTTP headers; targeted for
  IESG submission Aug 2025.
  <https://www.ietf.org/blog/ai-pref-progress/>
- **IPTC Generative-AI Opt-Out Best Practices v2.0**, Mar 2026.
  <https://iptc.org/std/guidelines/data-mining-opt-out/IPTC-Generative-AI-Opt-Out-Best-Practices.pdf>
- **Cloudflare Content-Signal directive**
  <https://contentsignals.org>
- **C2PA / CAWG Training and Data Mining Assertion** —
  `cawg.training-mining` label inside a C2PA manifest; C2PA itself
  clarified on 22 January 2026 that it is a *provenance* standard, not
  a do-not-train tag.

## Why this is directly load-bearing for `specint`

Our Common Crawl adapter walks arbitrary recipe pages. Our future
YouTube-CC and Pexels adapters walk arbitrary domains. Under the EU
DSM Directive Art. 4(3), a machine-readable opt-out is legally
enforceable — a rights holder who signals `tdm-reservation: 1` and
whose content we still ingest exposes us (and any downstream model
provider) to a copyright claim, and violates our hard constraint on
"no ToS violations". IPTC + IETF also normalise several *positive*
signals (`ai-train=no`, `Content-Signal: ai-train=no` in robots.txt)
that are *not* the same as blanket `Disallow: /` — a well-behaved
generic crawler is still allowed even if AI training is not.

## Signals we must read *before* ingesting anything from a web host

Ordered by specificity (more specific overrides less specific):

1. Per-resource **HTTP response header** `tdm-reservation: 1|0` and
   optional `tdm-policy: <url>`.
2. **HTML `<meta name="tdm-reservation" content="1|0">`** on the page.
3. **`/.well-known/tdmrep.json`** — array of `{ location, tdm-reservation, tdm-policy }`,
   with `location` matching robots.txt-style path rules.
4. **`robots.txt`** — both classic `User-agent: CCBot / GPTBot /
   ClaudeBot / Google-Extended / PerplexityBot` disallow lines, and
   the emerging `Content-Signal:` line with `ai-train=`,
   `ai-input=`, `search=` values.
5. **IPTC `plus:DataMining`** field in image/video XMP metadata (for
   media whose bytes we do actually fetch).
6. **CAWG `cawg.training-mining`** assertion inside a C2PA manifest.

If any of these signals prohibit AI training, we treat the record as
`License.RESTRICTED` regardless of the primary licence document.

## Transferable to `specint`

- **New module `src/specint/policy/optout.py`** with pure functions:
  - `parse_tdmrep_headers(headers) -> Reservation`
  - `parse_tdmrep_json(text) -> list[Reservation]`
  - `parse_robots_ai_directives(robots_txt, user_agent) -> AiPreference`
  - `parse_iptc_datamining_xmp(xmp: bytes) -> Reservation`
  All pure, all fixture-testable, no network.
- **New module `src/specint/policy/polite_fetcher.py`** — a thin
  wrapper around `httpx.Client` that (a) fetches `/.well-known/tdmrep.json`
  and `robots.txt` per-host at most once per crawl, (b) memoises the
  result, (c) refuses requests to any URL whose host reserves rights
  or whose per-resource signal is `tdm-reservation: 1`. Every
  `BaseSource` that touches HTTP must call through it.
- **New `VideoRecord` fields**:
  - `tdm_reservation: Literal["reserved","allowed","unknown"]`
  - `tdm_policy_url: HttpUrl | None`
  - `ai_preference: dict[str, str] | None` — the parsed
    Content-Signal directives, for auditability.
- **New CI test.** A fixture set under `tests/fixtures/policy/`
  containing (a) a robots.txt with mixed AI-train allow/disallow,
  (b) a `tdmrep.json`, (c) an HTML with meta-tag, (d) an HTTP
  header sample. Parser tests must be offline, deterministic, and
  cover every branch.

## NOT transferable

- Enforcement of TDMRep is legal, not technical. Reading the signal
  does not absolve us from a copyright claim if the underlying licence
  is unclear. Belt-and-braces: `License.UNKNOWN` still excludes from
  training corpora regardless of opt-out state.

## Adversarial notes

1. The signals frequently disagree. Our policy layer must record
   **every signal** and its resolution — not just the final verdict —
   so that a Reviewer-Agent can spot silent overrides.
2. Cloudflare's `Content-Signal` splits `ai-train` from `ai-input`.
   Ingestion for retrieval-augmentation vs training-corpus curation
   are *different* uses and our records should tag which use each
   signal permits.
