# C2PA Content Credentials (Spec 2.4, 2026)

- Spec: https://spec.c2pa.org/specifications/specifications/2.4/explainer/Explainer.html
- Implementation guidance: https://spec.c2pa.org/specifications/specifications/2.4/guidance/Guidance.html

## Claim

Every digital asset can carry a *C2PA Manifest*: a JUMBF-encoded,
X.509-signed set of assertions that describe origin (device, software,
AI generation status), edit history, and — critically for us — the
`cawg.training-mining` assertion that lets a creator opt-in or opt-out
of AI training. Manifests can travel inside the file container or as a
sidecar, and any compliant validator can check the certificate chain
and the hard-binding hash offline.

Well-behaved crawlers (Anthropic, OpenAI, Google are called out in
recent explainer articles) are expected to honour opt-outs at crawl
time. Ignoring `cawg.training-mining: notAllowed` is a direct
violation of the creator's expressed licence and — depending on
jurisdiction — of emerging regulation (EU AI Act Art. 53, UK "trusted
provenance" work).

## Evidence

- Standard is production. `c2patool` CLI, Adobe / Microsoft / Sony
  cameras, TikTok, Meta, and YouTube already stamp or verify
  manifests on some content.
- Assertions include `c2pa.actions` (created/edited/placed),
  `c2pa.hash.data` (SHA-256 hard binding), `c2pa.claim.signature`
  (COSE_Sign1), `cawg.training-mining` (opt-in/out).
- The hard-binding hash lets us detect *any* byte-level modification —
  a stronger integrity guarantee than the recorded-only provenance we
  have today.

## Steal

1. **Payload SHA-256 today, C2PA read-support tomorrow.** Extend
   `Provenance` with `payload_sha256: str | None`. Compute it on any
   raw HTTP payload we parse. This costs one hash and gives us the
   hard-binding property C2PA promises, minus the signature.
2. **Read (do not sign) C2PA manifests.** When a source exposes them
   (JUMBF box in an MP4, or a `.c2pa` sidecar), parse and enforce
   `cawg.training-mining`. If `notAllowed`, downgrade to
   `License.RESTRICTED` regardless of the surface CC label. Add a
   test with a synthetic JSON fixture (no real crypto — parsing only).
3. **Follow the trust list.** Do not attempt to sign our own manifests
   yet — that requires a CA-anchored X.509 chain. Filed as follow-up.

## Implications for specint

- Feeds `docs/plan-2026-07-16.md` → Provenance (H5) deliverables:
  `payload_sha256` in Provenance + a `git rev-parse` helper for
  `extractor_git`.
- Feeds License audit (Q1): a C2PA opt-out beats a CC-BY label. We
  should emit a `n_c2pa_optouts_honored` counter in the audit map.
- Anti-feed: **do not** stamp or serve C2PA manifests we did not
  originate. Passing through third-party manifests is fine (and
  encouraged); minting new ones without a trust anchor is worse than
  nothing.
