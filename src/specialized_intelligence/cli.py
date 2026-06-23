"""``si`` CLI entrypoint.

Today (day 1) the CLI exposes only ``si version`` and ``si stages``.
Future days will add ``si discover``, ``si acquire``, ``si curate ...``
each as a thin wrapper around a `Stage` subclass.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from specialized_intelligence import __version__
from specialized_intelligence.licenses import LicenseNorm, policy_for

app = typer.Typer(help="Specialized-Intelligence data pipeline CLI.")
console = Console()


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def licenses() -> None:
    """Print the license policy table.

    Useful for humans reviewing what the pipeline will and won't ship.
    """
    table = Table(title="License policy", show_lines=False)
    table.add_column("License", style="bold")
    table.add_column("Training")
    table.add_column("Redistribute bytes")
    table.add_column("Attribution")
    table.add_column("Share-alike")
    for lic in LicenseNorm:
        pol = policy_for(lic)
        table.add_row(
            lic.value,
            "yes" if pol.eligible_for_training else "no",
            "yes" if pol.may_redistribute_bytes else "no",
            "yes" if pol.requires_attribution else "no",
            "yes" if pol.requires_share_alike else "no",
        )
    console.print(table)


@app.command()
def stages() -> None:
    """List the pipeline stages defined in db_structured.md."""
    declared = [
        ("discover", "0.1.0", "candidate videos from sources"),
        ("acquire", "0.1.0", "license-aware download / manifest"),
        ("curate.clip", "0.1.0", "shot-aware split"),
        ("curate.filter", "0.1.0", "motion / aesthetic / OCR / content-type"),
        ("curate.embed", "0.1.0", "cosmos-embed1 or InternVideo2 embeddings"),
        ("curate.dedup", "0.1.0", "semantic dedup + contamination check"),
        ("annotate.caption", "0.1.0", "DenseStep2M-style structured caption"),
        ("annotate.procedural", "0.1.0", "per-step verb/noun/state grounding"),
    ]
    table = Table(title="Pipeline stages")
    table.add_column("stage")
    table.add_column("version")
    table.add_column("purpose")
    for name, ver, purpose in declared:
        table.add_row(name, ver, purpose)
    console.print(table)


if __name__ == "__main__":
    app()
