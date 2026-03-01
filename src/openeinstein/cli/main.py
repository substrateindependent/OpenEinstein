"""OpenEinstein CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from openeinstein import __version__

app = typer.Typer(help="OpenEinstein control plane CLI")
run_app = typer.Typer(help="Manage campaign runs", invoke_without_command=True)
pack_app = typer.Typer(help="Install and inspect campaign packs")
approvals_app = typer.Typer(help="Manage approval state")

app.add_typer(run_app, name="run")
app.add_typer(pack_app, name="pack")
app.add_typer(approvals_app, name="approvals")


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
