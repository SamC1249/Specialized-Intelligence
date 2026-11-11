# Artifact — The Common Pile v0.1 (Kandpal et al., arXiv:2506.05209, Jun 2025)

**URL:** https://arxiv.org/pdf/2506.05209
**Datasets:** `common-pile/youtube`, `common-pile/youtube_filtered` on HF.
**Access date:** 2026-11-11.

## One-paragraph summary

The Common Pile is an 8TB dataset of public-domain and
openly-licensed *text* assembled under the Open Knowledge Foundation's
Open Definition 2.1 (effectively: CC-BY, CC-BY-SA, CC0, PD, and
MIT-style software licenses — explicitly **excluding NC and ND**).
The YouTube component is the piece most relevant to us: rather than
trusting the per-video CC-BY flag (which is routinely
license-laundered by re-uploaders), the authors **manually curated
over 2,000 YouTube channels** that consistently release original
openly-licensed speech content, then enumerated their videos via the
YouTube API (metadata only) and transcribed audio with Whisper. The
result: 1,129,692 documents (≈470,000 hours) of audio and
transcripts.

## Why this matters for Specialized-Intelligence

1. **License laundering is the single biggest failure mode of
   "scrape CC-BY tags at scale" pipelines.** The paper is explicit
   about excluding YouTube Commons, OpenAlex, and the HN Kaggle dump
   because they could not verify license provenance. Our current
   `License.UNKNOWN` default is correct in principle, but we have no
   mechanism to *downgrade* a CC-BY-tagged record if the upstream is
   known to be unreliable. H2 of today's plan addresses this with a
   `license_verified` orthogonal flag.
2. **Channel-level trust beats file-level trust.** This is the
   methodology we should mirror for cooking: build (and version) a
   `src/specint/sources/_curated/cooking_channels.yaml` list of
   creators with high confidence their uploads are original. The
   list itself is a check-in, auditable, and rejectable in review.
3. **The scale is a useful calibration anchor.** 2,000 curated
   channels → 470k hours. If we get to a comparable curated-channel
   list for cooking, we should expect 5–50k hours, not 470k —
   cooking is a narrower slice. A number much larger than this
   probably means we have let laundered content back in.
4. **They publish their pipeline code.** `nkandpa2/youtube-commons`
   on GitHub uses SQLite for the channel/video catalog, YouTube Data
   API for metadata, and sharded `yt-dlp` audio-only downloads.
   The *metadata layer* of that design (channel allowlist →
   `playlistItems.list` → `videos.list` with
   `videoLicense=creativeCommon`) is directly adoptable by us; the
   audio download stage is out of scope until we add real media
   handling.

## Direct quotes worth preserving

- "We consider 'openly licensed' to mean any license that meets the
  Open Knowledge Foundation's Open Definition 2.1. … CC NC
  (non-commercial) and ND (no derivatives) licenses are not
  considered open under this definition and we therefore do not
  include content distributed under these licenses."
- "License laundering is a notoriously hard problem to identify
  exhaustively in practice. Copyright owners may also change the
  license they associate with their content."
- "We set strict standards for data sourcing, only including data
  from sources where we were confident that the licensing
  information was provided by the copyright holder, which
  ultimately led us to exclude certain sources such as OpenAlex,
  YouTube Commons, and the Hacker News dataset on Kaggle."

## Implementable takeaways for `Coding-Agent`

- Add `license_verified: bool = False` to `VideoRecord` and require
  **two independent license signals** before setting it True.
- Add a `curated_channels/` YAML allowlist (initially empty, with a
  `schema.json` + `test_curated_channel_schema.py`). Entries carry
  `channel_id`, `platform`, `domain`, `first_verified_at`,
  `last_verified_at`, `verifier`, `notes`. CI flags entries older
  than 180 days as stale.
- When we eventually enable a YouTube adapter (behind
  `SPECINT_RUN_INTEGRATION=1`), restrict queries to channels in the
  curated allowlist. Never do a bare keyword search for
  `videoLicense=creativeCommon` — that is exactly the laundering
  surface Common Pile warns about.
