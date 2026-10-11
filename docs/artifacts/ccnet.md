# CCNet — high-quality monolingual datasets from Common Crawl

- Paper: Wenzek et al., *CCNet: Extracting High Quality Monolingual
  Datasets from Web Crawl Data*, LREC 2020.
- PDF: <https://aclanthology.org/2020.lrec-1.494.pdf>

## What it is

CCNet is the canonical "take Common Crawl, make it useful" pipeline:

1. **Download** WET (text-only) shards of a crawl.
2. **Deduplicate paragraphs** using a normalised-form hash — removes
   boilerplate, menus, and site-wide cruft.
3. **Language ID** with fastText `lid.176.bin` (176 languages,
   single-CPU, 1k docs/s). Keep documents whose top-language score
   ≥ 0.5; discard the rest.
4. **Perplexity-based quality filter** — train a 5-gram Kneser–Ney KenLM
   on a *target domain* (Wikipedia by default) per language, then
   bucket pages into head / middle / tail by LM perplexity.

The pipeline is embarrassingly parallel and does not require any
model-based reranking at the primary filter stage.

## Why we care

- CCNet is the lower-cost backbone for everything we might want to do
  with Common Crawl for the long-tail recipe web. If we ever ingest
  more than a sample of CC in `common_crawl.py`, we should use CCNet-
  style paragraph dedup *before* schema.org extraction so that the
  JSON-LD blocks we see are from distinct pages, not 10 000 mirrors of
  the same WordPress theme.
- The `≥ 0.5` fastText threshold is a defensible, cheap language
  gate we can port directly to our text-density scoring. Our current
  `_score_text_density` is language-blind; a title in Lao scores the
  same as a title in English, which is wrong when our seed terms are
  English.
- **KenLM is Apache-licensed.** fastText is MIT. Both are fair game.

## Implementation hook

- `src/specint/quality/metrics.py` — add `_score_language_match(record,
  target_lang)` that returns 1.0 if detected language of
  `title + description` equals `target_lang` with confidence ≥ 0.5,
  else 0.0. Register in `WEIGHTS` with a small weight (0.05–0.10) and
  update tests. (Not shipped today: fastText adds ~130 MB of binary
  weights to the install. The adversarial decision is to document the
  hook now and gate the dependency behind an extra:
  `pip install specint[langid]`.)
- `src/specint/sources/common_crawl.py` — before `_walk_jsonld`,
  deduplicate by `sha256(normalise(paragraph))` across every ingested
  page in a single run. Today's dedup module is the generic kernel for
  this.
- `src/specint/compare/harness.py` — report `n_after_lang_filter` as a
  new benchmark column alongside `n_records`.

## Risks / disagreements

- CCNet was designed for *text*. Video pages are a weird edge: the
  interesting signal is often the `<script type="application/ld+json">`
  block, not the surrounding prose. Paragraph dedup over the raw page
  may incorrectly collapse two pages that have identical boilerplate
  but different videos. Mitigation: dedup *after* JSON-LD extraction,
  not before.
- Perplexity filtering biases toward Wikipedia-style prose. Recipe
  pages are list-heavy and will look "weird" to a Wikipedia LM. We
  should either train a KenLM on a recipe-corpus seed (Wikibooks
  Cookbook is CC-BY-SA and fits our allowlist) or skip LM filtering
  for the recipe track.
