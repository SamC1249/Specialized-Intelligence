# docs/artifacts/

External research notes referenced from `docs/plan-*.md`. Each file is
opinionated: it summarizes a paper or system in ≤ 300 words and closes
with a **"How we'd use it here"** section that names concrete files
under `src/specint/` that a follow-up Coding-Agent PR would touch.

Adding a note:

1. File name: `YYYY-MM-DD-slug.md` — same date as the plan that first
   references it.
2. First line: `# <slug> — <one-line summary>`.
3. Include a `Source:` line with the arXiv id / URL and the license /
   redistributability status of the artefact itself.
4. Close with a **How we'd use it here** section. If the answer is
   "we wouldn't", say so and why — negative artefacts are still
   informative.
