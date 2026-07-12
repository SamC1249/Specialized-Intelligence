# db_structured.md

Canonical data structures used across backend, frontend (future), CLI, and
benchmark reports. **All other code must import these types — never
redefine them locally.**

## `License` (enum)

| Value           | Meaning                                                   |
| --------------- | --------------------------------------------------------- |
| `CC0`           | Public domain dedication.                                 |
| `CC_BY`         | Attribution required.                                     |
| `CC_BY_SA`      | Attribution + share-alike.                                |
| `PUBLIC_DOMAIN` | Out of copyright / US-gov work / pre-1928, etc.           |
| `OTHER_FREE`    | Not CC but verifiably redistributable (e.g. WTFPL video). |
| `UNKNOWN`       | Could not determine — **never used for training**.        |
| `RESTRICTED`    | Known not redistributable. Stored only as a URL pointer.  |

## `VideoRecord` (Pydantic model)

| Field             | Type             | Notes                                                                                    |
| ----------------- | ---------------- | ---------------------------------------------------------------------------------------- |
| `id`              | `str`            | `f"{source}:{source_native_id}"`. Stable across re-crawls.                               |
| `source`          | `str`            | Source slug, e.g. `wikimedia`, `archive_org`, `peertube`, `common_crawl`.                |
| `source_native_id`| `str`            | Whatever the upstream calls its primary key.                                             |
| `url`             | `HttpUrl`        | Canonical landing page URL. **Never** a CDN URL.                                         |
| `media_url`       | `HttpUrl \| None`| Direct media URL **only** if the license permits redistribution (CC0/CC-BY/CC-BY-SA/PD). |
| `title`           | `str`            | Source-provided title.                                                                   |
| `description`     | `str`            | Source-provided long description (may be empty).                                         |
| `language`        | `str \| None`    | BCP-47 if known, else `None`.                                                            |
| `duration_s`      | `float \| None`  | Seconds; `None` if unknown.                                                              |
| `width`           | `int \| None`    | Pixels.                                                                                  |
| `height`          | `int \| None`    | Pixels.                                                                                  |
| `fps`             | `float \| None`  | Frames per second.                                                                       |
| `license`         | `License`        | See enum above. Defaults to `UNKNOWN`.                                                   |
| `license_url`     | `HttpUrl \| None`| Direct link to license page or upstream license metadata.                                |
| `author`          | `str \| None`    | Required attribution string for CC-BY*.                                                  |
| `published_at`    | `datetime \| None`| UTC.                                                                                    |
| `keywords`        | `list[str]`      | Free-form tags from upstream.                                                            |
| `recipe_steps`    | `list[str]`      | Step-text if available (Common Crawl recipe schema).                                     |
| `provenance`      | `Provenance`     | Always present, see below.                                                               |

## `Provenance` (Pydantic model)

| Field            | Type        | Notes                                                |
| ---------------- | ----------- | ---------------------------------------------------- |
| `extractor`      | `str`       | Module path, e.g. `specint.sources.wikimedia`.       |
| `extractor_git`  | `str`       | Short git SHA at extraction time (or `dev`).         |
| `fetched_at`     | `datetime`  | UTC instant the upstream blob was retrieved.         |
| `query`          | `str`       | Serialized `SourceQuery`.                            |

## `SourceQuery` (Pydantic model)

| Field      | Type        | Notes                                       |
| ---------- | ----------- | ------------------------------------------- |
| `terms`    | `list[str]` | Free-text search terms, OR-ed at the API.   |
| `max_results` | `int`    | Hard cap per source per query.              |
| `language` | `str \| None`| Optional language hint (BCP-47).           |

## `BenchmarkResult` (Pydantic model)

Emitted by `specint.compare.harness.run`. One row per `(source, query)`
pair plus an aggregate `total` row. Stored under
`reports/compare-YYYY-MM-DD.json`.

| Field                   | Type      | Notes                                       |
| ----------------------- | --------- | ------------------------------------------- |
| `source`                | `str`     | Or `"__total__"` for the aggregate row.     |
| `query_terms`           | `list[str]` |                                           |
| `n_records`             | `int`     | Records returned.                           |
| `n_license_clean`       | `int`     | License in {CC0, CC_BY, CC_BY_SA, PD, OTHER_FREE}. |
| `total_duration_s`      | `float`   | Sum of `duration_s` (treats None as 0).     |
| `mean_quality`          | `float`   | Mean of `quality_score`.                    |
| `p50_quality`           | `float`   | Median quality.                             |
| `p90_quality`           | `float`   |                                             |
| `unique_authors`        | `int`     | Heuristic for diversity.                    |
| `notes`                 | `str`     | Free-form, e.g. fixture name in CI runs.    |

## `Domain` (Pydantic model)

Registered in `specint.domains`. The pipeline is *domain-agnostic*; a
Domain carries the minimum config needed to swap cooking → laboratory
(or surgery / sports / manufacturing) without any code change.

| Field                 | Type              | Notes                                                       |
| --------------------- | ----------------- | ----------------------------------------------------------- |
| `slug`                | `str`             | `^[a-z][a-z0-9_]*$`. Used in report file names and CLI.     |
| `display_name`        | `str`             | Human-readable.                                             |
| `seed_terms`          | `tuple[str, ...]` | Free-text search terms fed to each source's `search`.       |
| `procedural_verbs`    | `tuple[str, ...]` | Lowercase, single-token verbs. Used by the v2 quality scorer's `procedural_density` component. |
| `eval_blocklist_urls` | `tuple[str, ...]` | Placeholder for future decontamination against public evals. |

Registered slugs (2026-07-12): `cooking`, `laboratory`, `surgery`,
`sports`, `manufacturing`. Add a new domain by extending
`specint.domains` — nothing else should hard-code domain vocabulary.

## Deduplication

Dedup is a *pipeline* concern, not a `VideoRecord` field. See
`specint.pipeline.dedup.dedup_records` for the full contract. In
brief:

- We never mutate records; the dedup function returns a
  `DedupResult(records, duplicates, counters)`.
- Survivor selection is deterministic: highest license tier, longest
  known duration, lexicographically smallest `id`.
- Merge signals: canonical URL, media URL, and title-shingle Jaccard
  ≥ 0.8 within a duration bucket.

`BenchmarkResult` rows with source `"__total_deduped__"` reflect the
dedup output.

## Quality scorer versions

| Version | Function            | Components                                                                              |
| ------- | ------------------- | --------------------------------------------------------------------------------------- |
| v1      | `score_record_v1`   | license_clean, duration, resolution, text_density, has_steps.                           |
| v2      | `score_record_v2`   | v1 minus license_clean plus **license_tier** (graded) and **procedural_density** (domain-aware verb count). |

v2 is the default (`score_record`). v1 is preserved for ablation and
Kendall-τ continuity against `reports/baseline-2026-06-20.json`.

## Frontend / API contract (placeholder)

There is no HTTP API yet. When one is added, all request/response bodies
**must** reuse the Pydantic models above; do not redefine them in
`api/*.py`.
