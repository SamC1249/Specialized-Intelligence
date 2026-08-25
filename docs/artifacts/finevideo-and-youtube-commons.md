# FineVideo + YouTube-Commons — CC-BY YouTube aggregation

- **FineVideo:** <https://huggingface.co/datasets/HuggingFaceFV/finevideo>
- **YouTube-Commons (upstream):**
  <https://huggingface.co/datasets/PleIAs/YouTube-Commons>

## What it is

**YouTube-Commons** is a corpus that aggregates *audio transcriptions*
of YouTube videos which the uploader explicitly marked CC-BY (via
YouTube's own "Creative Commons — Attribution" licence toggle). This
is the exact metadata field AGENTS.md permits us to query via the
YouTube Data API. FineVideo (HF) then curates 43,751 of those videos,
adds long, time-coded structural annotations generated with Gemini +
GPT-4o, and republishes the whole thing under CC-BY 4.0 with per-video
provenance back to the original YouTube channel.

## Why it matters for Specialized-Intelligence

- **Existence proof.** People are already building million-scale
  CC-BY-only video corpora and getting them accepted at top venues.
  The "no paid, no ToS violations" constraint is *not* a soft ceiling
  on frontier data quality.
- **Blueprint for our YouTube-CC adapter (`W10`).** AGENTS.md permits
  the exact API call FineVideo/YouTube-Commons rely on:
  `search.list?videoLicense=creativeCommon`.
- **Benchmark target.** We can, from our own metadata, estimate how
  many FineVideo channels our crawler independently finds. Overlap →
  yield sanity check; disjoint hits → new territory.

## Concrete implementation ideas

- `src/specint/sources/youtube_cc.py`:
  - `parse(raw, query)` consumes the merged JSON of `search.list` +
    `videos.list?part=contentDetails,snippet,status`.
    Reject any record where `status.license != "creativeCommon"`.
    Emit `License.CC_BY` (that's the only licence YouTube exposes
    under this flag) and `media_url = None` (we are URL + metadata
    only, and YouTube's ToS forbids re-hosting).
  - `search(query)` gated behind `YOUTUBE_API_KEY` +
    `SPECINT_RUN_INTEGRATION=1`.
- Fixture: a two-page synthetic `search.list` + `videos.list` JSON
  pair mirroring the real schema, checked into
  `tests/fixtures/youtube_cc/`.
- Overlap-benchmark script (post-adapter):
  `python -m specint compare-overlap --against finevideo --field
  channel_id` → JSON to `reports/`. Requires downloading only the
  FineVideo *metadata* Parquet (small, CC-BY, permitted).
- **Ethics note:** Even under CC-BY, some YouTube channels revoke
  their CC toggle after upload; we must re-verify licence on every
  crawl and drop revoked entries. Add a nightly re-check job in the
  next iteration.
