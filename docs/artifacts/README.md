# docs/artifacts — Research Notes

One markdown file per external artifact (paper, dataset, tool, standard)
that materially shapes our design. Each note must contain:

1. **Citation** — title, authors, venue/year, permalink.
2. **One-paragraph summary** — what the artifact claims, in our own
   words.
3. **What it changes for `specint`** — bullet list of concrete
   pipeline/schema/CI changes we should make in response, with pointers
   into `docs/plan-*.md` entries.
4. **Attack surface** — one or two paragraphs on where we think the
   result is *fragile*, so future Reviewer/Adversarial-Agents can revisit.

Notes are *not* a substitute for `docs/plan-*.md`. Plans decide what we
build; artifacts capture *why*.
