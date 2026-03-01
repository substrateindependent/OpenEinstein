"""OpenEinstein CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from openeinstein import __version__
from openeinstein.tracing import TraceStore

app = typer.Typer(help="OpenEinstein control plane CLI")
run_app = typer.Typer(help="Manage campaign runs", invoke_without_command=True)
pack_app = typer.Typer(help="Install and inspect campaign packs")
approvals_app = typer.Typer(help="Manage approval state")
trace_app = typer.Typer(help="Trace inspection and export")

app.add_typer(run_app, name="run")
app.add_typer(pack_app, name="pack")
app.add_typer(approvals_app, name="approvals")
app.add_typer(trace_app, name="trace")


@app.command("version")
def version() -> None:
    """Print CLI version."""
    rprint(f"OpenEinstein {__version__}")


@run_app.callback()
def run_callback(
    ctx: typer.Context,
    campaign_path: Optional[Path] = typer.Argument(None, exists=True),
) -> None:
    """Start a campaign or call a run subcommand."""
    if ctx.invoked_subcommand is None:
        if campaign_path is None:
            raise typer.BadParameter("Provide a campaign path or a run subcommand.")
        rprint(
            f"Starting campaign from {campaign_path}: [yellow]not implemented yet[/yellow]"
        )


@run_app.command("status")
def run_status(run_id: str = typer.Argument("latest")) -> None:
    """Show status for a run."""
    rprint(f"Run {run_id}: [yellow]not implemented yet[/yellow]")


@run_app.command("wait")
def run_wait(run_id: str = typer.Argument("latest")) -> None:
    """Block until a run is complete."""
    rprint(f"Waiting for run {run_id}: [yellow]not implemented yet[/yellow]")


@run_app.command("events")
def run_events(run_id: str = typer.Argument("latest")) -> None:
    """Stream events for a run."""
    rprint(f"Streaming events for run {run_id}: [yellow]not implemented yet[/yellow]")


@run_app.command("stop")
def run_stop(run_id: str) -> None:
    """Stop a campaign run."""
    rprint(f"Stopping run {run_id}: [yellow]not implemented yet[/yellow]")


@run_app.command("resume")
def run_resume(run_id: str) -> None:
    """Resume a campaign run from checkpoint."""
    rprint(f"Resuming run {run_id}: [yellow]not implemented yet[/yellow]")


@pack_app.command("install")
def pack_install(source: str) -> None:
    """Install a campaign pack from a path or git URL."""
    rprint(f"Installing campaign pack from {source}: [yellow]not implemented yet[/yellow]")


@approvals_app.command("list")
def approvals_list() -> None:
    """List approval states."""
    rprint("Approval state: [yellow]not implemented yet[/yellow]")


def _trace_store() -> TraceStore:
    return TraceStore.from_path(Path(".openeinstein") / "openeinstein.db")


@trace_app.command("list")
def trace_list(run_id: str = typer.Argument("default")) -> None:
    """List spans for a run."""
    spans = _trace_store().list_spans(run_id)
    if not spans:
        rprint(f"No spans found for run {run_id}")
        return
    for span in spans:
        rprint(
            f"{span.id}: {span.span_name} "
            f"({span.started_at} -> {span.ended_at or span.started_at})"
        )


@trace_app.command("export")
def trace_export(
    run_id: str = typer.Argument("default"),
    output: Path = typer.Option(
        Path("trace-export.json"), "--output", "-o", help="Output OTLP JSON file path"
    ),
) -> None:
    """Export spans to OTLP JSON format."""
    payload = _trace_store().export_otlp_json(run_id)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rprint(f"Exported trace payload for run {run_id} to {output}")
