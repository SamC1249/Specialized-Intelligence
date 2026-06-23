# 2026-06-23 — Legal posture for video data collection

Author: `Adversarial-Agent`

This memo states the legal constraints the project will operate under. The
two summary rules are: **use the YouTube Data API, not scraping**, and
**redistribute only what the license unambiguously permits**.

---

## 1. YouTube

Two binding documents:

- **YouTube Terms of Service**: forbids accessing the service "using any
  automated means (such as robots, botnets or scrapers) except (a) in the
  case of public search engines, in accordance with YouTube's robots.txt
  file; or (b) with YouTube's prior written permission."
- **YouTube API Services — Developer Policies**: forbids API Clients from
  scraping YouTube or Google Applications directly or indirectly, or from
  obtaining scraped YouTube data from third parties.

Operational consequence:

- The only sanctioned channel is the **YouTube Data API v3**.
- Free tier: **10,000 units / day**. A `search.list` is 100 units, a
  `videos.list` is 1-3 units. At that quota we can discover at best
  ~100 candidate videos per day per project. Quota extensions are slow
  (multi-month) and not guaranteed.
- We **never** shard across multiple Google Cloud projects to multiply
  quota. That is an explicit policy violation.

Operational consequence #2: we restrict every Data API call to
`videoLicense=creativeCommon`. This is the only YouTube content for which
we can plausibly republish derived products (with attribution) under
CC-BY.

Operational consequence #3: even for CC-BY YouTube videos, we **prefer
manifest-only storage** (video URI + sha256 + timestamps) and resolve to
bytes at training time, mirroring the YouTube-Commons posture.

## 2. Creative Commons taxonomy

| License        | Reuse | Modify | Commercial | Share-Alike | Use in our pipeline?                                |
| -------------- | ----- | ------ | ---------- | ----------- | --------------------------------------------------- |
| CC0 / Public Domain | yes   | yes    | yes        | n/a         | **Yes** — full bytes can be stored & republished.   |
| CC-BY          | yes   | yes    | yes        | no          | **Yes** — store bytes; attribution mandatory.       |
| CC-BY-SA       | yes   | yes    | yes        | yes         | **Yes** — derived datasets must be released SA.     |
| CC-BY-ND       | yes   | no     | yes        | no          | **No** — we always modify (re-encode, clip).        |
| CC-BY-NC*      | yes   | yes    | no         | depends     | **Discovery-only** — never in training data.        |

Every record in our pipeline carries `license_norm` from a closed enum
(`CC0`, `CC_BY`, `CC_BY_SA`, `PD`, `CC_BY_NC*`, `UNKNOWN`). The
license-audit CI job (`scripts/audit_licenses.py`) fails the build if any
shard intended for training contains anything other than the first four.

## 3. Fair use

We do not rely on fair use. Two reasons:

1. Fair use is an *argument* in court, not an *allowance*. Until a court
   has ruled, every CC-NC or All-Rights-Reserved video in our corpus is a
   contingent liability.
2. We have a cleaner alternative (CC-BY + CC0 + PD + university lecture
   archives + Wikimedia Commons). The marginal value of pulling in
   ARR content is small compared to the legal complexity.

For benchmarks, where we only need to *evaluate* and never redistribute,
fair-use posture is acceptable; the benchmark loaders log the source URL
and license but never persist bytes.

## 4. EU AI Act, machine-readable opt-outs

Creative Commons is rolling out **preference signals** — machine-readable
tags indicating whether CC-licensed content may be used for AI training.
The EU AI Act's extraterritorial reach may make these globally binding.

Operational consequence: the `discover` stage must read and persist any
present opt-out signals (`robots.txt`, TDM reservation, CC preference
signal headers). The `acquire` stage must refuse content with a positive
opt-out flag, even if the underlying license would otherwise permit use.

## 5. Sources beyond YouTube (in order of license cleanliness)

| Source                       | License posture                                 | Estimated cooking-relevant volume |
| ---------------------------- | ----------------------------------------------- | --------------------------------- |
| Wikimedia Commons            | CC0 / CC-BY-SA only                              | small (hundreds of hours)         |
| Archive.org cookery shows    | mostly public-domain TV recordings              | medium (low thousands of hours)   |
| Vimeo "Creative Commons" tab | per-video CC tags (six variants + CC0)          | ~792k CC videos total; cooking slice unknown — discovery target |
| PeerTube federated instances | per-video, often CC                              | unknown; discovery target         |
| University lecture archives  | per-institution, often CC-BY-NC                  | useful for evaluation only        |
| YouTube `videoLicense=creativeCommon` | CC-BY only                              | the largest single source         |

Order of attack:

1. Wikimedia Commons (highest-quality license, smallest volume, fastest
   to ship).
2. Archive.org cookery (public domain, no rate-limit drama).
3. PeerTube federated crawl (long-tail, no quota).
4. Vimeo CC tab (rate-limited but clean).
5. YouTube Data API with `videoLicense=creativeCommon` (slowest funnel
   per unit of effort, but highest absolute volume).

## 6. Privacy

Cooking videos frequently incidentally show the uploader's face, kitchen,
and family. We treat this as PII:

- Per `db_structured.md` section 6, any future face-detection stage must
  emit a `face_blurred: bool` flag and CI enforces blur on `FULL_BYTES`
  exports.
- We never publish channel-level demographic aggregates beyond what the
  uploader has already published.

---

## Sources

- YouTube ToS: <https://www.youtube.com/t/terms>
- YouTube API Developer Policies: <https://developers.google.cn/youtube/terms/developer-policies>
- YouTube API pricing & quotas (2026 guide): <https://www.blotato.com/blog/youtube-api-pricing>
- YouTube-Commons (HF blog): <https://huggingface.co/blog/Pclanglais/youtube-commons>
- YouTube-Commons (HF dataset): <https://huggingface.co/datasets/pshishodia/YouTube-Commons>
- EleutherAI youtube-cc: <https://huggingface.co/datasets/EleutherAI/youtube-cc>
- Creative Commons & AI (ERCIM News 144): <https://ercim-news.ercim.eu/en144/special/creative-commons-licences-in-the-age-of-ai-challenges-and-opportunities>
- Vimeo Creative Commons: <https://vimeo.com/creativecommons>
- Data Provenance for video/speech/text: <https://alnap.cdn.ngo/media/documents/Bridging_data_provenance-text-speech-video.pdf>
