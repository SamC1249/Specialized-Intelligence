# EU AI Act — Art. 53(1)(d) training-data transparency template

- **Instrument:** *Explanatory Notice and Template for the Public
  Summary of Training Content for General-Purpose AI models*, adopted
  by the European Commission's AI Office on **24 July 2025** under
  Article 53(1)(d) of Regulation (EU) 2024/1689.
- **Applicability:** every provider of a GPAI model placed on the EU
  market on or after **2 August 2025**; pre-existing models must
  comply by **2 August 2027**. Free/open-source GPAI providers are
  **not** exempt from Art. 53(1)(c) copyright policy and 53(1)(d)
  summary.
- **Sources:**
  - <https://artificialintelligenceact.eu/high-level-summary/>
  - <https://regulations.ai/regulations/european-union-2025-7-template-training-summary>
  - <https://licensefoundry.com/eu-ai-act/>

## What the template requires

Three core information blocks, in the mandatory Commission format:

1. **Model / provider metadata.**
2. **Data-source categories used in training**, enumerated:
   public datasets, licensed datasets, crawled/scraped online content
   (with a **narrative description and the top contributing domains
   or domain groups**, feasibility permitting), user data, synthetic
   data, other sources.
3. **Processing and governance**:
   - confirmation of licensing arrangements for private/licensed data,
   - measures for respecting **text-and-data-mining opt-outs**
     (Art. 4(3) DSM Directive),
   - procedures for identifying and removing illegal content,
   - GDPR / data-protection posture (DPIA where applicable).

The summary is deliberately *not* a work-by-work manifest but must be
**detailed enough that rights-holders can exercise their remedies**.
Under Article 101 the Commission can fine providers for supplying
**incorrect, incomplete or misleading information** *separately* from
any underlying copyright breach — meaning our summary must be
substantiated by internal records.

## Transferable to `specint`

- **Our provenance schema is already close.** `Provenance` records
  `extractor`, `extractor_git`, `fetched_at`, `query`. Missing for the
  template: the *domain*/host of the origin, and the *legal basis*
  (CC-BY / CC-BY-SA / CC0 / PD / API-ToS-permitted / opt-out-checked).
- **New CLI command: `python -m specint transparency`.** Consumes a
  batch of `VideoRecord` JSON dumps and emits a JSON document that
  matches the Commission template's mandatory sections. Fields:
  - `data_sources[i].category` ∈ {public_dataset, api_permitted,
    crawled_web, licensed, synthetic, other}
  - `data_sources[i].description` — free-text narrative
  - `data_sources[i].top_domains` — top-N eTLD+1 counts
  - `data_sources[i].license_mix` — histogram over the `License` enum
  - `governance.opt_out_signals_respected` — TDMRep / IPTC / robots-AI
    tokens (see `2026-tdmrep-and-aipref.md`)
  - `governance.illegal_content_filter` — pipeline used
  - `provenance_snapshot.extractor_git` — the exact commit set
- **Compliance test in CI.** Every fixture-driven benchmark must be
  round-trippable through the transparency exporter without missing
  required fields. A failing transparency export blocks the PR.

## NOT (yet) transferable

- The template also asks about *pre-training data used to train the
  model*, i.e. downstream of us. `specint` produces the *input record*
  to that pipeline, not the model itself. We only own the fields the
  template calls "data sources".

## Adversarial notes

1. The Commission can fine on *misleading* summaries alone. This means
   silently mislabeling a UNKNOWN-licensed record as CC-BY is worse
   than dropping it. Our `License.UNKNOWN` default is defensible; the
   quality scorer must never assign a license-clean bonus without a
   verifiable license string.
2. The template's "top domains" requirement is a *dedup pressure test*:
   if 80 % of our records collapse to two domains, the corpus is not
   really "internet-scale" and the summary will make that obvious.
