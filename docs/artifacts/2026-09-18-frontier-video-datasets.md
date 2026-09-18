# Frontier video-model data landscape — 2026-09-18

Research digest compiled by `Adversarial-Agent` before writing today's plan.
The goal of this note is to make sure our sourcing strategy is *comparably
sized* to what actual frontier labs are training on, and to pull in
signals we currently ignore.

## 1. What the frontier is actually training on

### 1.1 V-JEPA 2 / 2.1 (Meta, 2025–2026)

- **Mixture:** VideoMix22M ≈ 22 M samples, > 1 M hours video.
  - Something-Something v2 168 K clips, weight 0.056 (egocentric, action)
  - Kinetics 400/600/700, 733 K clips, weight 0.188 (exocentric, action)
  - HowTo100M, 1.1 M videos, ~134 000 h, weight 0.318 (instructional)
  - YT-Temporal-1B (curated), 19 M clips, ~1.6 M h, weight 0.188 (general)
  - ImageNet 1 M images, weight 0.250
- **V-JEPA 2.1 (VisionMix163M):** YT-1B up-weighted 3.8×, ImageNet replaced
  with LVD-142M. Direct evidence that a **curated web-video slice** is the
  single most important corpus for a video world model — bigger than every
  action-labelled dataset combined.
- **World-model post-training:** only < 62 h of unlabelled Franka
  teleoperated video from DROID is required *once* the encoder is trained
  on 1 M+ h of internet video.

Citations:

- V-JEPA 2 paper: <https://arxiv.org/html/2506.09985v1>
- JEPA Wiki training recipes: <https://mishig-jepawiki.hf.space/wiki/concepts/training-recipes>

### 1.2 Sekai / Sekai2 (NeurIPS 2025 / arXiv 2026)

- Sekai-Real-Walking: 6552 source videos, 299 173 samples, ~4986 h,
  first-person walking; camera trajectories included.
- Sekai2 extends to 2826 h across 113 countries with hierarchical
  annotations (subject motion, environment dynamics, static scene, camera)
  and 982 panoramic sequences with loops/revisits — explicitly designed
  for "long-term spatial memory and geometrically consistent world models."
- **Legal status:** YouTube-derived, so per-video CC-BY status must be
  verified rather than assumed. Their toolchain is CC-compatible; the
  video content itself carries whatever the original uploader chose.

Citations:

- Sekai codebase: <https://github.com/Lixsp11/sekai-codebase>
- Sekai2 arXiv: <https://arxiv.org/html/2608.09449>

### 1.3 P-JEPA (2026)

- Uses frozen V-JEPA 2.1 frame features on **EgoExo4D**, **EgoProceL**,
  and **Assembly101**.
- Take-level masked latent prediction over 30-minute videos induces
  representations that align with within-video temporal progress.
- Signal for us: procedural, long-horizon *supervision* comes for free
  from long single-take videos — so long-single-take should be a
  first-class **quality dimension** in our scorer, not just resolution.

Citation: <https://arxiv.org/html/2606.23256>

## 2. Legally-clean web-video corpora we should mine

### 2.1 PleIAs YouTube-Commons (CC-BY-4.0)

- 2 063 066 YouTube videos, 22.7 M transcripts, ~45 B words, released as
  Parquet on the Hugging Face Hub. Every row carries `video_id`,
  `video_link`, `channel`, `date`, `license`, `original_language`,
  `word_count`, `character_count`.
- Distribution is 71 % English original, with auto-translated variants in
  fr/es/de/ru/it/nl.
- **Why this matters:** it is the biggest existing whitelist of CC-BY
  YouTube video IDs *anywhere*, ~20× the size of FineVideo. Our
  `AGENTS.md` allowlist already permits YouTube for
  `videoLicense=creativeCommon`; consuming YouTube-Commons offline lets
  us skip the 100–1000/day search-bucket quota entirely.
- **Direct load:** `load_dataset("PleIAs/YouTube-Commons")`. Rows are
  transcripts; join back to `video_link` for the canonical URL.

Citations:

- HF dataset: <https://huggingface.co/datasets/PleIAs/YouTube-Commons>
- Common Corpus (ICLR 2026 oral): <https://arxiv.org/html/2506.01732v1>

### 2.2 FineVideo (CC-BY, HuggingFaceFV)

- 43 751 YouTube videos, ~3425 h, mean 4.7 min, 122 categories including
  cooking, DIY, science, sports.
- Metadata includes scene, character, mood, and audio–visual dynamics
  annotations.
- We should ingest as a *labelled* validation corpus for our quality
  scorer.

Citation: <https://huggingface.co/datasets/HuggingFaceFV/finevideo>

### 2.3 Common Crawl URL Index + Web Data Commons

- Common Crawl URL Index (formerly Columnar Index; renamed June 2026) is
  Parquet, queryable via Athena / Spark / DuckDB / Polars. Columns
  include `content_mime_type`, `content_languages`,
  `url_host_registered_domain`, `warc_filename`, `warc_record_offset`.
- **Direct plan:** filter for HTML with `content_mime_type LIKE
  'text/html%'` on recipe/domain allowlists, then use
  `CCIndexWarcExport` to pull WARC records and parse the embedded
  `application/ld+json` in-process (we already do that in
  `sources/common_crawl.py`).
- Web Data Commons ships pre-extracted JSON-LD subsets from CC-MAIN-
  2024-42, but **VideoObject is not among the published class-specific
  subsets**. `schema.org/Movie` is — and that gives us feature films (US
  public-domain film archives that syndicate Movie schema).

Citations:

- CC URL Index: <https://commoncrawl.org/url-index>
- CC index Notebook: <https://github.com/commoncrawl/cc-notebooks>
- WDC 2024-12: <https://webdatacommons.org/structureddata/2024-12/stats/schema_org_subsets.html>

### 2.4 PeerTube — federated, actually big

- Fediverse Stats snapshot 2026-05-09: **2 095 active instances,
  1 680 711 videos, 1.26 B views**.
- Our current adapter hits **3 instances**. This is the highest-leverage
  under-utilisation in the repo.
- **Fix:** use SepiaSearch (`https://sepiasearch.org/api/v1/search/videos`)
  which federates over all instances that opted into it. Fall back to
  per-instance for instances not indexed by Sepia.

Citations:

- PeerTube stats: <https://libera.site/channel/peertube?mid=7f07c563-5631-4012-9ef8-2ef0e7bab802>
- Cooking channels example: `peertube.zalasur.media/c/food_and_cooking_channel`

### 2.5 Wikimedia Commons Impact Metrics (2025-→)

- New Analytics Query Service endpoints expose *actual play counts* for
  video files on `upload.wikimedia.org`, monthly, per category, per
  file, per referrer, per agent type.
- 465 curated main categories opted in as of May 2026 (categories 7
  levels deep so coverage is broad).
- **Use:** treat play count as a weak external validation signal for our
  metadata-only quality score. Report Spearman ρ between our score and
  log(plays). If ρ < 0.2 our weights are noise.

Citations:

- Endpoint reference: <https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/media-files.html>
- Commons Impact Metrics: <https://commons.wikimedia.org/wiki/Commons:Commons_Impact_Metrics>

## 3. Hard-target domain: surgery (world-model stress test)

The AGENTS.md mission calls out surgery as a canonical "difficult video"
target. State of the art open corpora:

- **PhaKIR** (MICCAI 2024 / *Data in Brief* 2026): 8 complete
  laparoscopic cholecystectomies, 485 875 phase-labelled frames, 19 435
  instrument-segmented frames. License: **CC-BY-NC-SA** → maps to our
  `License.RESTRICTED`. Do **not** ingest media; store only URL +
  provenance for downstream evaluators.
- **LEMON / LemonFM** (CVPR 2026): 4000+ videos, 938 h across 35
  procedure types, "publicly available on request." Not permissive
  enough for our allowlist.
- Implication: for surgery, **there is essentially no CC-BY corpus at
  scale**. Our job is (a) index what exists with correct license tags
  and (b) discover long-tail CC-licensed surgical demonstrations on
  Wikimedia Commons + Internet Archive (e.g. `medlineplus`, `NIH`,
  military-medicine archival footage).

Citations:

- PhaKIR paper: <https://arxiv.org/html/2511.06549>
- LEMON CVPR 2026: <https://openaccess.thecvf.com/content/CVPR2026/html/Che_LEMON_A_Large_Endoscopic_MONocular_Dataset_and_Foundation_Model_for_CVPR_2026_paper.html>

## 4. Take-aways for our roadmap

1. **Quality of the *slice* beats quality of the *scraper*.** V-JEPA 2.1
   moved the needle by re-weighting YT-1B, not by changing extractors.
   Our comparison harness needs a **weighted-mixture** row on top of
   per-source rows.
2. **Popularity is a free weak label** — use Commons Impact Metrics play
   counts to validate our metadata-only score.
3. **CC-BY YouTube video IDs are already curated in the open.** We do not
   need to run YouTube Data API `search.list` at all; we should ingest
   PleIAs YouTube-Commons as a first-class source.
4. **Long single-take runtime is the sleeper quality feature** for
   world-model pretraining (P-JEPA evidence). Add a
   `single_take_bonus` component to the scorer.
5. **We are massively under-utilising PeerTube.** Switch fanout to
   SepiaSearch.
6. **Surgery domain is a license desert.** Ship a *URL-only* adapter with
   correct RESTRICTED tagging so we can still enumerate what exists.
