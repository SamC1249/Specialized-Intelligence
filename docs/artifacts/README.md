# `docs/artifacts/` — research notes

Each file in this directory distils one external paper, dataset, or
pipeline into:

1. **What it is** — one-paragraph summary.
2. **Why we care** — the specific problem in `specint` it informs.
3. **Implementation hook** — the exact module path or test we would
   change if we adopted the idea.
4. **Risks / disagreements** — where our hard constraints (no paid
   datasets, no ToS violations, offline tests, provenance mandatory)
   diverge from the paper.

Add a new note whenever a plan references an outside source. Keep notes
small (≤ 200 lines) — they are *pointers*, not reproductions. Always
cite with a stable URL and quote only short, fair-use snippets.
