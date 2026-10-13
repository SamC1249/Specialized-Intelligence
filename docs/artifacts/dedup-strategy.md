# dedup-strategy.md — Cross-source deduplication cascade

Problem: the same clip can land in our index three times — once from
Wikimedia Commons, once from a PeerTube mirror, once as a Common Crawl
`VideoObject` on a recipe blog. The current harness counts all three in
`total_duration_s` and in `n_license_clean`. This inflates every yield
metric and silently poisons the ranking that drives downstream
decisions.

This doc proposes a **three-stage cascade** — cheapest-signal first —
and specifies what each stage must deliver to be mergeable into the
`compare` harness.

## Design goals

1. **Metadata-first.** Stage 1 touches no media bytes.
2. **Deterministic and offline-testable.** Every stage must take a
   `list[VideoRecord]` and return `(list[VideoRecord], DedupReport)`.
   No upstream calls.
3. **Reversible.** `DedupReport` records *why* a record was dropped
   (which other record subsumed it, by which rule). We never silently
   delete rows.
4. **Composable with the harness.** `compare.run_comparison` grows an
   optional `dedup=` parameter; the harness emits a per-source
   `n_dedup_dropped` column so a source cannot game the benchmark by
   duplicating itself.

## Public shape

```python
# src/specint/dedup/types.py
class DedupReport(BaseModel):
    dropped: list[tuple[str, str, str]]  # (loser_id, winner_id, rule)
    kept: int
    rules_hit: dict[str, int]


# src/specint/dedup/pipeline.py
def dedup(
    records: list[VideoRecord],
    stages: list[DedupStage] | None = None,
) -> tuple[list[VideoRecord], DedupReport]: ...
```

Where `DedupStage` is `Protocol[call(list[VideoRecord]) ->
tuple[list[VideoRecord], DedupReport]]` so every stage is independently
unit-testable.

---

## Stage 1 — Canonical-URL / native-id (O(N), metadata-only)

- **Signal.** Normalise `url` (strip query, strip fragment, lowercase
  host, drop `www.`, canonicalise known shorteners), then group by
  `(normalised_url,)`. Within a group keep the record whose `license`
  is highest-redistributability (`CC0 > CC_BY > CC_BY_SA > PD > OTHER_FREE
  > UNKNOWN > RESTRICTED`) and whose `provenance.fetched_at` is newest.
- **Also deduplicate** by `(source, source_native_id)` exact match
  (defensive: Reposted search results from the same adapter.)
- **Cost.** Pure Python dict; O(N).
- **Expected recall.** Catches ~60–80% of our observed dupes in the
  fixture set once we add a Commons/PeerTube-mirror fixture.
- **Delivery.** Blocks `plan-2026-10-13.md` deliverable 8.

## Stage 2 — Title + description MinHash LSH (O(N·k), metadata-only)

- **Signal.** Shingle `title + " \n " + description + " \n " + " ".join(recipe_steps)`
  into 5-grams of characters (not words — robust to localisation
  spacing). Compute a 128-permutation MinHash signature per record.
  Insert into `datasketch.MinHashLSH(threshold=0.85, num_perm=128)`.
  Group candidate pairs, verify by computing exact Jaccard on shingle
  sets, keep the record with the richer metadata (longer description,
  more `recipe_steps`, higher resolution).
- **Why 0.85?** Empirically high enough that distinct recipes with
  similar titles ("Garlic butter pasta" vs "Garlic butter pasta with
  lemon") survive; low enough to catch republished uploads that only
  rephrase the description.
- **Cost.** `datasketch` is a pure-Python dep already permissively
  licensed (MIT); CPU-only. One-time ~2 ms/record for signature; LSH
  query O(1) amortised. 1M records ≈ 30 minutes single-threaded. For
  >10M switch to `datasketch`'s Redis backend or FED-style GPU MinHash.
- **Known pitfall.** Different *episodes* of the same cooking show
  share boilerplate ("Welcome back to Kitchen Nightmares…"). We will
  need a boilerplate stripper (per-source rules) before MinHash sees
  the text. Ship stripper rules alongside the adapter that provides
  the records.
- **Delivery.** Follow-on PR after Stage 1 ships green.

## Stage 3 — Perceptual video hash (frames required, future)

- **Signal.** Extract N keyframes (N = 8 or `duration_s / 10`
  whichever is smaller), compute DCT-based pHash per keyframe,
  concatenate into a per-video signature. LSH over Hamming distance.
  Verify candidates by frame-sequence alignment.
- **Status.** *Out of scope until we have a frame-fair-use pipeline.*
  Documented here so the earlier stages do not foreclose this design.
  Any `VideoRecord` field we add in Stage 1/2 must be reused — not
  conflicting — with a future `phash: str | None` field.
- **References.** `docs/artifacts/papers.md` §C2, §C3 (LSH framework
  and ViDupe cascade shape).

---

## How the harness consumes dedup output

Patch to `specint.compare.harness.run_comparison`:

```python
def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    dedup: Callable[[list[VideoRecord]], tuple[list[VideoRecord], DedupReport]] | None = None,
) -> list[BenchmarkResult]:
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    per_source_dropped: dict[str, int] = {}
    for source, records in sorted(by_source.items()):
        scored = score_records(records)
        if dedup is not None:
            scored, report = dedup(scored)
            per_source_dropped[source] = len(report.dropped)
        all_scored.extend(scored)
        rows.append(
            aggregate(
                source,
                query.terms,
                scored,
                notes=notes,
                n_dedup_dropped=per_source_dropped.get(source, 0),
            )
        )
    # Cross-source dedup for the __total__ row:
    if dedup is not None:
        all_scored, total_report = dedup(all_scored)
    rows.append(
        aggregate(
            "__total__",
            query.terms,
            all_scored,
            notes=notes,
            n_dedup_dropped=len(total_report.dropped) if dedup else 0,
        )
    )
    return rows
```

`BenchmarkResult` grows one new field (`n_dedup_dropped: int`) with a
default of `0` so existing baseline JSON files remain readable.

## Test matrix for the Coding-Agent

| Test                                                    | Must prove                                                       |
| :------------------------------------------------------ | :--------------------------------------------------------------- |
| `test_dedup_stage1_canonical_url_same_source`           | Same URL within one source → one survives.                      |
| `test_dedup_stage1_canonical_url_cross_source`          | Same URL across Commons / PeerTube → Commons wins (highest licence tier). |
| `test_dedup_stage1_native_id_only`                      | Two records with different URLs but same (source, native_id).   |
| `test_dedup_stage2_minhash_title_variant`               | Two records with semantically-identical titles survive→collapse. |
| `test_dedup_stage2_minhash_different_recipes`           | "Garlic butter pasta" vs "Garlic butter shrimp" survive both.    |
| `test_dedup_report_roundtrip`                           | `DedupReport.dropped` always references ids that existed.        |
| `test_benchmark_regression_includes_n_dedup_dropped`    | Baseline file gets a new column with default 0.                 |

All tests offline. Fixtures live under `tests/fixtures/dedup/`.
