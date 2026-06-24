# plan.md — Rolling agent log

Each entry is 1-2 lines. Format:

```
- [ISO-8601 UTC]  <Identity>  <commit>  <summary>
```

See `docs/plan/<YYYY-MM-DD>.md` for the full reasoning behind each entry.

---

- 2026-06-20T17:17:30Z  Adversarial-Agent  c9e909d  Bootstrapped the repo: AGENTS.md, db_structured.md, README, plan.md, day-one adversarial review (docs/plan/2026-06-20.md), 6 paper/source artifacts (HowTo100M, Panda-70M, InternVid, Summer-22B+DreamDojo, V3C, legal-landscape), components (manifest_schema, DCT pHash), e2e pipeline dry-run, unit + e2e tests (24 passing), CI workflows, and 2 custom pre-commit hooks (forbid-youtube-domains, forbid-paid-sources). Core argument: in 2026, given Chmura v. Snap and the April-2026 creator class actions, byte-level YouTube acquisition is out of scope; the cooking-video flywheel must start from license-clean sources (Wikimedia, Internet Archive, Vimeo CC) and optimize for world-model utility, not aesthetic alone.
- 2026-06-24T17:30:00Z  Adversarial-Agent  PENDING  Day-two adversarial work: shipped `components/eval_blocklist.py` (DataComp-style step-3 eval-set decontamination, plus 6 unit + 2 e2e tests), wired `--eval-blocklist` into the dry-run pipeline (now v0.0.2), and clarified in db_structured.md §2.3 that an empty shard is a valid "we rejected everything" signal. Added a third pre-commit hook `require-license-confidence-in-adapters` that fails any `components/sources/*.py` mentioning `license` without a `license_confidence` field, plus a CI unit-test matrix on Python 3.11 + 3.12. Wrote 4 new artifact notes (V-JEPA 2 cluster retrieval, HD-EPIC, PeerTube federated-crawl recipe, DataComp filtering for video) and `docs/plan/2026-06-24.md`. Tests: 39 passed, 1 skipped.
