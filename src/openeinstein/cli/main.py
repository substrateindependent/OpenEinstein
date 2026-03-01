"""OpenEinstein CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from openeinstein import __version__
from openeinstein.evals import EvalRunner, discover_eval_suites
from openeinstein.persistence import CampaignDB
from openeinstein.tracing import TraceStore

app = typer.Typer(help="OpenEinstein control plane CLI")
run_app = typer.Typer(help="Manage campaign runs", invoke_without_command=True)
pack_app = typer.Typer(help="Install and inspect campaign packs")
approvals_app = typer.Typer(help="Manage approval state")
trace_app = typer.Typer(help="Trace inspection and export")
eval_app = typer.Typer(help="Eval suite commands")

app.add_typer(run_app, name="run")
app.add_typer(pack_app, name="pack")
app.add_typer(approvals_app, name="approvals")
app.add_typer(trace_app, name="trace")
app.add_typer(eval_app, name="eval")


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


def _db_path() -> Path:
    return Path(".openeinstein") / "openeinstein.db"


def _trace_store() -> TraceStore:
    return TraceStore.from_path(_db_path())


@eval_app.command("list")
def eval_list(
    path: Path = typer.Option(Path("evals"), "--path", "-p", help="Eval suite root directory")
) -> None:
    """List available eval suites."""
    db = CampaignDB(_db_path())
    runner = EvalRunner(db)
    suite_files = discover_eval_suites(path)
    if not suite_files:
        rprint(f"No eval suites found under {path}")
        db.close()
        return
    for suite_file in suite_files:
        suite = runner.load_suite(suite_file)
        rprint(f"{suite.name}: {suite_file}")
    db.close()


@eval_app.command("run")
def eval_run(
    suite_file: Path = typer.Argument(..., exists=True, readable=True),
    run_id: str | None = typer.Option(None, "--run-id", help="Optional eval run id"),
) -> None:
    """Run an eval suite and persist results."""
    db = CampaignDB(_db_path())
    runner = EvalRunner(db)
    suite = runner.load_suite(suite_file)
    report = runner.run_suite(suite, run_id=run_id)
    rprint(
        f"Eval run {report.run_id} ({report.suite_name}): "
        f"{report.passed_cases}/{report.total_cases} passed"
    )
    for case in report.case_results:
        rprint(f"- {case.case_name}: {'PASS' if case.passed else 'FAIL'}")
    db.close()


@eval_app.command("results")
def eval_results(run_id: str = typer.Argument("latest")) -> None:
    """Show persisted eval results by run id."""
    db = CampaignDB(_db_path())
    if run_id == "all":
        results = db.get_eval_results()
    elif run_id == "latest":
        all_results = db.get_eval_results()
        if not all_results:
            rprint("No eval results found.")
            db.close()
            return
        latest_run = all_results[-1].run_id
        results = [row for row in all_results if row.run_id == latest_run]
        run_id = latest_run
    else:
        results = db.get_eval_results(run_id)

    if not results:
        rprint(f"No eval results found for run {run_id}.")
        db.close()
        return

    passed = sum(1 for row in results if row.passed)
    rprint(f"Eval results for run {run_id}: {passed}/{len(results)} passed")
    for row in results:
        rprint(f"- {row.suite_name}/{row.case_name}: {'PASS' if row.passed else 'FAIL'}")
    db.close()


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
