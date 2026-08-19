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
| `n_unique_after_dedup`  | `int`     | Records surviving cross-source dedup (URL + title-shingle Jaccard). |
| `license_clean_ratio`   | `float`   | `n_license_clean / n_records`.              |
| `mean_procedural_density` | `float` | Mean of the metadata-only "procedural density" signal (verbs+units+quantities). |
| `languages_seen`        | `list[str]` | Sorted set of BCP-47 codes, either upstream-provided or stoplist-detected. |
| `scorer_profile`        | `str`     | Which scorer profile produced `mean_quality` — currently `v1` or `v2_procedural`. |

## Scorer profiles

Quality is metadata-only and profile-selectable via
`specint.quality.PROFILES`:

| Profile           | Formula                                                                            |
| ----------------- | ---------------------------------------------------------------------------------- |
| `v1`              | Weighted blend of license/duration/resolution/text_density/has_steps (see `metrics.py`). |
| `v2_procedural`   | `v1 + 0.25 * procedural_density * (1 - v1)`, clamped to `[0, 1]` — additive-boost so `v2 >= v1` for every record and the Pareto verdict against `v1` cannot regress. |

## Deduplication

`specint.quality.dedupe` returns a `DedupReport` clustering records by:

1. Canonical URL hash (`canonicalize_url` strips scheme, `www.`,
   query/fragment, Wikimedia thumb prefixes, and Archive.org
   `download/<id>` → `details/<id>`).
2. Title-shingle Jaccard `>= 0.85` **and** (same author OR duration
   within 5%).

Deterministic union-find. The cluster representative prefers
license-clean records so downstream training corpora keep the freely
redistributable copy.

## Frontend / API contract (placeholder)

There is no HTTP API yet. When one is added, all request/response bodies
**must** reuse the Pydantic models above; do not redefine them in
`api/*.py`.
