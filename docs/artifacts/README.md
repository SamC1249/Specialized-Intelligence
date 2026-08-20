# docs/artifacts

Short, source-of-truth research notes on external papers, datasets, and
tooling that shape our data-collection strategy.

Each artifact file:

- Names the exact paper / repo / dataset (with URL and access date).
- States, in one paragraph, what it does and why it matters for
  **legal, internet-scale, high-quality video collection**.
- Lists concrete **ideas we can steal** (with pointer to which module
  they would land in) and **ideas we should refuse** (usually because
  they require ToS-violating or copyrighted data).

If you are adding a new artifact, keep the file under ~200 lines. Deep
implementation should live in `src/specint/` behind a benchmark entry —
not in these notes.
