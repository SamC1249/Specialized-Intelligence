# Specialized-Intelligence

Internet-scale, legally-clean video data pipelines for **frontier video
world models**, starting with the cooking-video vertical.

This repo is run by named LLM agents. Read [`AGENTS.md`](AGENTS.md) first
for the project's mission, the agent roster, and the contract every PR
must satisfy. The full data and pipeline contract lives in
[`db_structured.md`](db_structured.md). Daily plans go in
[`docs/plan/`](docs/plan/) and research notes go in
[`docs/artifacts/`](docs/artifacts/).

The rolling 1-2 line summary of each day's work is in
[`plan.md`](plan.md).

## Quickstart (developer)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
pytest -q
si licenses        # print the license-policy table
si stages          # list the pipeline stages
```

## Why this exists

Frontier video world models (Cosmos, DreamDojo, OmniWorld) are bottlenecked
on **data quality**, not on compute. Most of the easy public corpora
(HowTo100M, EPIC-KITCHENS, Ego4D) have already been mined; redoing them
gives no differentiation. The wedge this project bets on is:

> Federated, license-clean, procedurally-grounded long-horizon video,
> with structured per-step state annotations, with a public contamination
> audit against every popular benchmark.

See [`docs/plan/2026-06-23.md`](docs/plan/2026-06-23.md) for the day-1
adversarial framing.

## License

Apache-2.0 for code. Derived datasets are licensed per-shard based on
their source-material license trail; see the `datacard.md` shipped with
each shard release.
