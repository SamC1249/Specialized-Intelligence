# plan.md — Rolling agent log

Each entry is 1-2 lines. Format:

```
- [ISO-8601 UTC]  <Identity>  <commit>  <summary>
```

See `docs/plan/<YYYY-MM-DD>.md` for the full reasoning behind each entry.

---

- 2026-06-20T17:17:30Z  Adversarial-Agent  c9e909d  Bootstrapped the repo: AGENTS.md, db_structured.md, README, plan.md, day-one adversarial review (docs/plan/2026-06-20.md), 6 paper/source artifacts (HowTo100M, Panda-70M, InternVid, Summer-22B+DreamDojo, V3C, legal-landscape), components (manifest_schema, DCT pHash), e2e pipeline dry-run, unit + e2e tests (24 passing), CI workflows, and 2 custom pre-commit hooks (forbid-youtube-domains, forbid-paid-sources). Core argument: in 2026, given Chmura v. Snap and the April-2026 creator class actions, byte-level YouTube acquisition is out of scope; the cooking-video flywheel must start from license-clean sources (Wikimedia, Internet Archive, Vimeo CC) and optimize for world-model utility, not aesthetic alone.
- 2026-06-23T17:21:00Z  Coding-Agent  2d2fef7  Merged both 2026-06-20 Adversarial-Agent bootstraps (51ab components + 45be src/specint) and implemented §7 open questions: eval-contamination blocklist (Hamming-8 gate wired into the pipeline dry-run), per-record license-confidence scorer, cuisine/language/license bias audit, world-model-utility proxy ranker, and a systematic 5-strategy comparison harness with deterministic Jaccard overlap matrix. New CLI commands `specint audit` / `specint strategies`. 81 tests pass (34 new); CI matrixed on py3.11/3.12.
