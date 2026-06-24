# Specialized-Intelligence

A research repo for **collecting internet-wide, license-clean video data
for frontier world models.** The current vertical is **cooking videos**;
the methodology is intentionally domain-general.

> Read [`AGENTS.md`](./AGENTS.md) before contributing.
> The data and API contract lives in [`db_structured.md`](./db_structured.md).
> Daily plans and adversarial reviews live in [`docs/plan/`](./docs/plan/).
> Paper / source notes live in [`docs/artifacts/`](./docs/artifacts/).

## Why this repo exists

Frontier world models live and die by data quality. Most public
"large-scale" video datasets are either (a) sourced from YouTube and now
under active 2026 litigation (*Chmura v. Snap*, the YouTube creator
class actions vs. Amazon/OpenAI/Apple) or (b) research-license-only
(EPIC-KITCHENS, HD-EPIC, Ego4D). We want a third path: **systematic,
license-clean, world-model-useful** video data, primarily from
Wikimedia Commons, Internet Archive, Vimeo CC, Flickr PD, government
open archives, and CC-permissive PeerTube communities.

See [`docs/research/cooking-video-flywheel.md`](./docs/research/cooking-video-flywheel.md)
for the long-form argument.

## Quickstart

```bash
python -m pip install -e ".[dev]"
pre-commit install
pytest -q                        # unit tests
python scripts/pipeline_dry_run.py --out artifacts/manifests
pytest tests/e2e -q              # end-to-end against the dry-run manifests
```

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Repo contract; read first. |
| `db_structured.md` | Manifest schemas (raw_video, clip, shard) and per-function contract template. |
| `plan.md` | Rolling 1–2-line agent log. |
| `docs/plan/<date>.md` | Per-day adversarial review and plan. |
| `docs/artifacts/` | Per-paper / per-source notes. |
| `docs/research/` | Long-form essays and arguments. |
| `components/` | Reusable Python primitives (manifest schema, pHash). |
| `scripts/` | Standalone CLIs (pre-commit hooks, pipeline dry run). |
| `tests/unit/` | Schema, pHash, and hook tests. |
| `tests/e2e/` | End-to-end pipeline + manifest-lint tests. |
| `.github/workflows/ci.yml` | Lint, unit, e2e, manifest-lint jobs. |

## Hard rules

1. **No YouTube byte-level acquisition.** Enforced by the
   `forbid-youtube-domains` pre-commit hook and the matching CI job.
2. **No paid sources, no IP rotation, no TPM bypass.**
3. **`license == "UNKNOWN"` ⇒ `excluded == true`.** Enforced in
   `components/manifest_schema.py`.
4. **Every artifact carries provenance**: canonical URL, license, SPDX
   string, attribution, collected-at timestamp, pipeline version.

## Status

Bootstrapping. See `docs/plan/2026-06-20.md` for the current adversarial
review and the immediate roadmap.
