# EU AI Act — Article 53 + TDM opt-outs — Cheat-sheet

- **Effective date for GPAI obligations:** 2 August 2026 (three weeks
  before this note). Non-compliance ceiling: **3 % of global turnover
  or €15 M**, whichever is higher.
- **Legal basis for the opt-out itself:** Article 4(3) of the DSM
  Directive (EU 2019/790) — rights reservations must be *machine
  readable* to be effective.
- **Practical checklist (from the AI Act Service Desk & GPAI Code of
  Practice):**
  1. Respect `robots.txt` per IETF RFC 9309 (Disallow, crawl-delay).
  2. Respect `ai.txt` files.
  3. Respect TDM Reservation Protocol markers:
     - HTTP response header: `TDM-Reservation: 1`
     - `<meta>` tag: `<meta name="tdm-reservation" content="1">`
     - `/.well-known/tdmrep.json` file.
  4. Never circumvent paywalls or DRM.
  5. Exclude known-piracy sites.
  6. Publish a mandatory *training-data summary* (AI Office template,
     released 2025-07-24). For scraped content, list the top 10 % of
     domain names by volume (top 5 % or 1,000 domains for
     SMEs/startups).
  7. Provide a rightsholder contact point.

## Signal semantics we must implement correctly

| Signal      | Default when absent | Default when file exists but silent |
| ----------- | ------------------- | ----------------------------------- |
| `robots.txt`| **allowed**         | allowed unless a matching `Disallow` |
| TDMRep      | **allowed**         | allowed (silence == permission)     |
| `ai.txt`    | **refused**         | refused (silence == refusal, per the AI Preferences WG draft) |

The TDMRep and `ai.txt` polarities are **opposite** — this is the
number-one implementation bug we must avoid.

## Data model impact

Add a `RightsSignal` sub-record to `Provenance`:

```
RightsSignal:
  fetched_at:   datetime  # when we checked
  source_url:   HttpUrl   # exact origin
  robots_allowed:  bool | None       # None == not checked
  tdmrep:       "reserved" | "allowed" | "absent"
  ai_txt:       dict[str, bool] | None   # media_category -> allowed
  raw:          str        # verbatim response bodies (bounded)
```

A record whose `robots_allowed is False` or `tdmrep == "reserved"` or
`ai_txt["video"] is False` **must not** be marked as
`License.is_redistributable`, regardless of what the licence tag says.
This is a hard override in the scorer and in any downstream
"training-clean" filter.

## Comparison-first commitment

Add a benchmark column `n_rights_clean` alongside `n_license_clean`. The
two will disagree — and the disagreement rate per source is itself an
interesting research metric.
