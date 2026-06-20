# Paper note: HowTo100M (Miech et al., 2019)

- **Paper**: *HowTo100M: Learning a Text-Video Embedding by Watching
  Hundred Million Narrated Video Clips* — Miech, Zhukov, Alayrac,
  Tapaswi, Laptev, Sivic. ICCV 2019. arXiv:1906.03327.
- **Headline numbers**: 1.22M YouTube videos, 136M ASR-aligned clips,
  134,472 hours, 23,611 visual tasks (cooking, hand crafting, personal
  care, gardening, fitness, etc.).

## What it teaches us

1. **WikiHow as a topic ontology.** They started from WikiHow's ~120k
   "How to ..." articles, restricted to 12 visual-physical categories
   and verbs, and produced 23,611 tasks. **This ontology is reusable for
   us** even if we don't touch a YouTube video — we can use it to *plan
   what cooking demonstrations to look for in license-clean sources*.
2. **ASR-narration alignment is a free supervision signal.** They paired
   each clip with the ASR transcript covering its time range, exploiting
   the strong assumption that narrators describe what they're doing.
   *Adapt to our setting:* for license-clean cooking videos we collect,
   run open-source ASR (e.g. Whisper-class) and emit
   `caption_source = "asr"` rows.
3. **Quality heuristics they used (paraphrased)**:
   - drop videos with < 100 views (proxy for amateurish content)
   - drop videos with < 100 ASR words
   - drop videos longer than 2,000 s
   - dedup by YouTube ID (does not catch re-uploads)
4. **Limitation we can fix**: their dedup is by YouTube ID, which misses
   re-uploads / re-encodes. Our pHash + embedding pipeline catches these.

## What we *cannot* take from it

- **The ID list.** Using HowTo100M's ID list to fetch YouTube bytes runs
  into the *Chmura v. Snap* fact pattern. We treat it strictly as a
  topic-ontology hint.

## Ideas to implement

- **WikiHow seed list → license-clean search.** For each of the 23,611
  visual tasks, query Wikimedia Commons, Internet Archive, Vimeo CC, and
  CC Search (OpenVerse) and harvest license-clean results. Most tasks
  will return nothing; the ones that return non-empty results are the
  near-term coverage map of *what we can actually train on*.
- **ASR-aligned clip extraction.** For every retained video, run
  Whisper-class ASR locally; align word-timestamps to PySceneDetect
  scene boundaries to emit clip rows whose `caption` is the ASR span.
