# 06 — "Frames as fair-use derivatives" doctrine (DO NOT SHIP YET)

**Status:** research question only. Explicitly deferred until a
future adversarial plan takes a position on it.
**Hypothesis served:** none yet — this is a *scope-expansion
proposal* that must be approved before any code lands.

## The question

AGENTS.md allows "fair-use derivatives (frames + URL provenance,
not bulk redistribution of copyrighted media)." That hints at a
pathway where we would:

1. Sample N frames per minute from a RESTRICTED video.
2. Downsample each frame to ≤ 512px on the long edge, strip EXIF.
3. Store the frame **with** the original canonical URL as mandatory
   provenance.
4. Distribute the frames for *analysis* (not training) under a
   research exemption claim.

This is extremely attractive from a yield standpoint — most of the
procedural-video internet is RESTRICTED by default — and extremely
risky legally.

## Prior art

- **HD-VILA-100M** and **Panda-70M**'s source material are all
  harvested from third-party platforms; both projects explicitly
  **do not redistribute the videos**, only metadata and URLs, with
  takedown-on-request. Panda-70M: *"We will remove the video samples
  from our dataset / Github / project webpage / technical
  presentation as long as you need it."*
- **LAION-BVD** (Aug 2026) is 1.3B URLs + 80M downloaded videos (10M
  hours) with scene splits and captions, released explicitly
  **not for commercial use**. See
  [`docs/artifacts/papers/README.md`](./papers/README.md).
- **The Pile v2** debate established that redistributing text under
  "fair use for research" is contested jurisdiction-by-jurisdiction,
  particularly in the EU after the DSM Directive's Art. 4 opt-out.

## Why we are not shipping it today

- The hard constraint "No paid datasets, no paywall scraping, no ToS
  violations" is unambiguous about *downloads* of ToS-protected media
  even if we only keep frames. Most video platforms' ToS explicitly
  prohibit automated downloading, full stop.
- Even if we never download the full file (byte-range sampling of a
  video segment to extract a frame), that is still an automated fetch
  of copyrighted media, which almost all platforms disallow by ToS.
- A "frames exemption" would need written sign-off from a lawyer and
  jurisdiction-specific policy. That is not a code-change-sized
  decision.

## If we ever revisit

The minimum policy before any frame extraction code lands:

1. A `LICENSE_POLICY.md` reviewed by counsel that enumerates:
   - which jurisdictions we claim to operate under,
   - the fair-use / fair-dealing / text-and-data-mining (TDM)
     exceptions we rely on,
   - the retention policy for frames (how long, who can access,
     how takedowns propagate).
2. A `takedown@` contact and tooling to remove records by URL hash.
3. An audit log — every frame extraction records the exact
   `(url, timestamp, extractor_git, byte_range)` tuple.
4. A "frames only, no video" constraint enforced at the storage
   layer, not just in code review.
5. An explicit **negative** benchmark: measure how much yield we gain
   vs. the sum of license-clean sources *before* adopting the risk.
   If permissive sources already saturate our training budget, the
   risk/benefit is zero.

## Takeaway for specint

Keep this file as the project's answer to the inevitable "why don't
you just scrape YouTube and clip frames?" question. The next
adversarial plan should either (a) propose a concrete pre-condition
checklist to move this to "under evaluation", or (b) explicitly
re-affirm the "URL + metadata only" boundary.
