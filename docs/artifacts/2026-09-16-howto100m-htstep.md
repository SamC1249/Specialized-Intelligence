# HowTo100M + HT-Step

- **HowTo100M** — Miech, Zhukov, Alayrac, Tapaswi, Laptev, Sivic. ICCV 2019.
  [arXiv:1906.03327](https://arxiv.org/abs/1906.03327) ·
  [project page](https://www.di.ens.fr/willow/research/howto100m/).
- **HT-Step** — Afouras, Mavroudi, Nagarajan, Wang, Torresani. NeurIPS 2023
  Datasets & Benchmarks.
  [paper (PDF)](https://proceedings.neurips.cc/paper_files/paper/2023/file/9d58d85bfc041b4f901c62ba37a3f322-Paper-Datasets_and_Benchmarks.pdf).

## What they built

HowTo100M assembles **136M weakly-paired (clip, caption) pairs from
1.22M narrated YouTube instructional videos** across 23k tasks (cooking
is the largest slice). Data collection is unsupervised: the pairing
comes from automatically-transcribed narrations. HT-Step then adds
**~116k dense temporal step annotations across ~20k cooking videos
(~2.1k hours)** by aligning each video to its corresponding *wikiHow*
article, giving a **4,958-step taxonomy** grounded in human-written
procedural knowledge.

## What we can steal

- **Task inventory via wikiHow.** wikiHow's article corpus is CC-BY-NC-SA;
  the *taxonomy of task names* (article titles + section headings) is a
  factual list and is safe to use as a query seed for any of our
  license-clean sources. Concretely: mine wikiHow cooking-category
  article titles offline (dump), then feed them as `SourceQuery.terms`
  into every adapter. Expected effect: order-of-magnitude yield jump on
  Wikimedia Commons + Archive.org vs. our current 2-term seed.
- **Article ↔ video weak alignment as a supervision signal.** When a
  recipe page in Common Crawl has a `Recipe.recipeInstructions` list
  *and* a co-located `VideoObject`, we already get quasi-HT-Step-style
  step supervision for free. We should keep `recipe_steps` in our
  `VideoRecord` (already done) and add a per-record `n_steps` quality
  component.
- **ASR narration as supervision.** For anything we *are* allowed to
  download (Commons/Archive/PeerTube), whisper-scale ASR gives us
  free (transcript, timestamp) supervision. This is post-collection
  work but the schema should carry an optional `transcript_url`
  pointer.
- **Task-diversity target = 23k activities.** Any collection run whose
  unique-task count is stuck at O(10) is under-crawled by 3+ orders of
  magnitude. Bake this into the benchmark harness as a hard "diversity"
  metric.

## What we must *not* copy

- HowTo100M is a URL list; the *videos are all-rights-reserved YouTube
  content*. We must not host or redistribute them. Any pipeline that
  materialises HowTo100M media into training corpora is off-limits for
  us. The **taxonomy is factual → OK**, the media list is not.
- HT-Step annotations are CC-BY-NC 4.0 (per the NeurIPS release). Our
  training corpora are commercial-intent, so treat HT-Step labels as
  reference only, not as training targets.

## Implementation hooks

- `src/specint/quality/metrics.py` → add `n_steps` bounded component
  (currently `has_steps` is binary; a saturating log(1+n) captures
  procedural density better).
- `src/specint/sources/wikimedia.py`, `.../archive_org.py`,
  `.../peertube.py` → accept a *task inventory* file (line-delimited
  wikiHow-style titles) and iterate `SourceQuery` over batches of
  terms.
- `src/specint/compare/harness.py` → new metric
  `n_unique_tasks_seen` derived from a query→record mapping so we
  measure the diversity ceiling of each source.
