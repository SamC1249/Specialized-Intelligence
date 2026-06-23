# Legal landscape for video-data collection (snapshot: 2026-06-20)

> Adversarial-Agent's compilation of the live legal/contractual constraints
> that shape what we can and cannot do. Not legal advice; this is a working
> document for engineering decisions.

## Headline findings

- **YouTube is, in 2026, the most legally hazardous source for AI-training
  byte-level acquisition.** Multiple class-action complaints have been filed
  against major AI labs (Snap, Amazon, OpenAI, Apple) alleging that their
  use of `yt-dlp`, IP-rotation, and YouTube-derived ID-list datasets
  (HD-VILA-100M, Panda-70M, HowTo100M) constitutes **DMCA §1201
  anti-circumvention**.
- **Creative Commons tagging on YouTube does *not* override YouTube's ToS.**
  The platform-level prohibition on automated download still applies. The
  V3C dataset (Vimeo, ~3,800h CC video) chose Vimeo over YouTube
  *specifically* because Vimeo's ToS *does* permit downloading CC
  content for redistribution-permitted reuse, while YouTube's does not.
- **License-clean alternatives exist** but have a long-tail problem of
  inconsistent license tagging (especially Wikimedia Commons), so a
  per-source license adapter must emit both an SPDX string *and* a
  confidence value.

## The active 2026 cases (as of this writing)

### *Chmura v. Snap* (C.D. Cal.)

- **Theory**: Snap built Panda-70M (an internally-curated 70M-clip
  video-text dataset) by sourcing from HD-VILA-100M's YouTube ID list and
  using `yt-dlp` + IP rotation to acquire bytes at scale. Plaintiffs
  argue this is anti-circumvention of YouTube's TPMs and breach of YouTube's
  ToS for the (uploader) class members.
- **Why this matters to us**: it puts every YouTube-ID-list dataset
  (HowTo100M, HD-VILA-100M, InternVid, Panda-70M, WebVid) under a
  legal-risk cloud for *byte-level* reuse. The metadata (titles,
  timestamps, ASR text) is differently situated from the bytes.

### Amazon / OpenAI / Apple — YouTube creator class actions (April 2026)

- **Theory**: Same DMCA-§1201 + ToS-breach pattern. Plaintiffs are YouTube
  uploaders alleging unlawful scraping for video-generation training.
- **Implication**: This is no longer one outlier complaint; it's a
  pattern. Treat YouTube acquisition as actively litigated risk.

## License posture per source we plan to use

| Source | What the ToS says | What CC tagging means there | Our posture |
|---|---|---|---|
| **YouTube** | Prohibits automated download, including via APIs other than the official streaming player. | Irrelevant to acquisition rights. | **Out of scope for bytes.** Metadata-only via official Data API where possible. |
| **Vimeo** | Permits download of CC-licensed videos for the uses the CC license allows (this is the V3C precedent). | Honored. | **In scope** for CC-tagged content; per-item license check. |
| **Wikimedia Commons** | All hosted media must be CC-BY/-SA, CC0, or PD by site policy. | Authoritative. | **In scope.** Caveat: occasionally the *file* is CC-BY but the *description page* lists conflicting metadata; per-item adapter must reconcile and emit confidence. |
| **Internet Archive** | Permits download per item license. Prelinger Archives are PD by donor declaration. | Per item. | **In scope** with per-item license parse. |
| **Flickr** | Permits download of CC and PD videos. | Per item. | **In scope.** |
| **Common Crawl** | The crawl itself is public. | n/a — Common Crawl is metadata-and-HTML, not media. | **In scope as a discovery layer**; resolve any video URLs to one of the above license-clean sources before downloading bytes. |
| **PeerTube federated instances** | Per instance and per video. | Often CC by community norm. | **In scope** for CC; per-item check. |

## Provenance ledger requirements

For every retained artifact (`raw_video` row), we record:

- `canonical_url` (page URL, not media URL)
- `media_url` (if downloaded)
- `license` (SPDX-style string)
- `license_url`
- `attribution`
- `collected_at` (ISO-8601 UTC)
- `pipeline_version`
- `sha256` of the media file (post-download, post-normalization)

Without these, a future takedown / DMCA / opt-out request cannot be
satisfied. *Provenance is the price of legitimacy.*

## Engineering rules that fall out of all this

1. **Hard ban**: any code that calls `yt-dlp` against a YouTube URL.
   Pre-commit hook `forbid-youtube-domains` enforces this in the repo
   layer.
2. **Hard ban**: code that rotates IPs or proxies for video acquisition.
3. **Soft block**: any new `source` enum value requires a row in
   §"License posture per source" above before merge.
4. **Default exclude**: `license == "UNKNOWN"` ⇒ `excluded = true`.
5. **Takedown path**: every published shard manifest must carry an opt-out
   contact and a documented removal SLA.
