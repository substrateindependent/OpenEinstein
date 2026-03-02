"""OpenEinstein CLI entrypoint."""

from __future__ import annotations

import json
import shutil
import webbrowser
from pathlib import Path

import typer
import uvicorn
import yaml  # type: ignore[import-untyped]
from rich import print as rprint

from openeinstein import __version__
from openeinstein.campaigns import CampaignConfigLoader
from openeinstein.evals import EvalRunner, discover_eval_suites
from openeinstein.gateway import FileBackedControlPlane
from openeinstein.gateway.web import DashboardConfig, DashboardDeps, create_dashboard_app
from openeinstein.persistence import CampaignDB
from openeinstein.reports import CampaignReportGenerator
from openeinstein.security import ApprovalsStore, SecurityScanner
from openeinstein.skills import SkillRegistry
from openeinstein.tools import LatexToolchain
from openeinstein.tracing import TraceStore

app = typer.Typer(help="OpenEinstein control plane CLI")
run_app = typer.Typer(help="Manage campaign runs", invoke_without_command=True)
pack_app = typer.Typer(help="Install and inspect campaign packs")
approvals_app = typer.Typer(help="Manage approval state")
trace_app = typer.Typer(help="Trace inspection and export")
eval_app = typer.Typer(help="Eval suite commands")
context_app = typer.Typer(help="Context assembly utilities")
latex_app = typer.Typer(help="LaTeX publishing toolchain commands")
sandbox_app = typer.Typer(help="Sandbox diagnostics")
campaign_app = typer.Typer(help="Campaign data management commands")
report_app = typer.Typer(help="Campaign report synthesis commands")

app.add_typer(run_app, name="run")
app.add_typer(pack_app, name="pack")
app.add_typer(approvals_app, name="approvals")
app.add_typer(trace_app, name="trace")
app.add_typer(eval_app, name="eval")
app.add_typer(context_app, name="context")
app.add_typer(latex_app, name="latex")
app.add_typer(sandbox_app, name="sandbox")
app.add_typer(campaign_app, name="campaign")
app.add_typer(report_app, name="report")


@app.command("version")
def version() -> None:
    """Print CLI version."""
    rprint(f"OpenEinstein {__version__}")


@app.command("dashboard")
def dashboard(
    port: int = typer.Option(8420, "--port", min=1, max=65535),
    host: str = typer.Option("127.0.0.1", "--host"),
    base_path: str = typer.Option("/", "--base-path"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open a browser tab"),
    allow_insecure_remote: bool = typer.Option(
        False,
        "--allow-insecure-remote",
        help="Allow non-local HTTP binding without TLS safeguards",
    ),
) -> None:
    """Start the dashboard web server and optionally open it in a browser."""
    if host not in {"127.0.0.1", "localhost"} and not allow_insecure_remote:
        raise typer.BadParameter(
            "Remote HTTP access is blocked by default. Use --allow-insecure-remote explicitly."
        )

    config = DashboardConfig(
        base_path=base_path,
        bind=host,
        port=port,
        allow_insecure_remote=allow_insecure_remote,
    )
    dashboard_app = create_dashboard_app(
        config=config,
        deps=DashboardDeps(control_plane=_control_plane()),
    )

    url_path = "/" if base_path in {"", "/"} else f"/{base_path.strip('/')}/"
    url = f"http://{host}:{port}{url_path}"
    if not no_open:
        webbrowser.open(url)

    rprint(f"Dashboard listening at {url}")
    uvicorn.run(dashboard_app, host=host, port=port, log_level="info")


@app.command("init")
def init_workspace(workspace: Path = typer.Option(Path(".openeinstein"), "--workspace")) -> None:
    """Initialize local OpenEinstein workspace directories."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "control-plane").mkdir(parents=True, exist_ok=True)
    (workspace / "artifacts").mkdir(parents=True, exist_ok=True)
    (workspace / "cache").mkdir(parents=True, exist_ok=True)
    env_example = Path(".env.example")
    if not env_example.exists():
        env_example.write_text(
            "\n".join(
                [
                    "ANTHROPIC_API_KEY=",
                    "OPENAI_API_KEY=",
                    "S2_API_KEY=",
                    "ADS_API_KEY=",
                    "ZOTERO_API_KEY=",
                    "ZOTERO_USER_ID=",
                    "CROSSREF_MAILTO=",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    rprint(f"Initialized workspace at {workspace}")


@app.command("scan")
def scan(
    paths: list[Path] | None = typer.Argument(
        None, help="Paths to scan for risky security patterns"
    ),
) -> None:
    """Scan repository files for risky patterns."""
    scan_targets = paths or [Path("configs"), Path("src"), Path("campaign-packs")]
    scanner = SecurityScanner()
    findings = scanner.scan_paths(scan_targets)
    if not findings:
        rprint("No risky patterns found.")
        return
    for finding in findings:
        rprint(
            f"{finding.severity.upper()} {finding.rule_id} "
            f"{finding.path}:{finding.line} {finding.message}"
        )
    raise typer.Exit(code=1)


@run_app.callback()
def run_callback(ctx: typer.Context) -> None:
    """Run command namespace callback."""
    if ctx.invoked_subcommand is None:
        raise typer.BadParameter("Provide a run subcommand.")


@run_app.command("start")
def run_start(campaign_path: Path = typer.Argument(..., exists=True)) -> None:
    """Start a campaign run."""
    control = _control_plane()
    run_id = control.start_run()
    control.emit_event(run_id, "campaign_path_set", {"campaign_path": str(campaign_path)})
    rprint(
        f"Started run {run_id} for campaign {campaign_path}. "
        "Use `openeinstein run status <run_id>` to monitor progress."
    )


@app.command("results")
def results_summary(run_id: str = typer.Argument("latest")) -> None:
    """Show candidate and failure summary for a run."""
    db = CampaignDB(_db_path())
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    candidates = db.get_candidates(resolved)
    failures = db.get_failure_log(resolved)
    rprint(
        f"Run {resolved}: {len(candidates)} candidates, "
        f"{len(failures)} failures"
    )
    db.close()


@app.command("export")
def export_results(
    run_id: str = typer.Argument("latest"),
    output: Path = typer.Option(Path("campaign-export.json"), "--output", "-o"),
) -> None:
    """Export candidate/failure data for a run to JSON."""
    db = CampaignDB(_db_path())
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    payload = {
        "run_id": resolved,
        "candidates": [row.__dict__ for row in db.get_candidates(resolved)],
        "failures": [row.__dict__ for row in db.get_failure_log(resolved)],
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    db.close()
    rprint(f"Exported run {resolved} to {output}")


@app.command("config")
def config_command(
    validate: bool = typer.Option(False, "--validate", help="Validate config shape"),
    path: Path = typer.Option(
        Path("configs/openeinstein.example.yaml"),
        "--path",
        help="Configuration file path",
    ),
) -> None:
    """Show or validate a config file."""
    if not path.exists():
        raise typer.BadParameter(f"Config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not validate:
        rprint(json.dumps(payload, indent=2, default=str))
        return
    if not isinstance(payload, dict):
        raise typer.BadParameter("Config root must be a mapping")
    if "model_routing" not in payload:
        raise typer.BadParameter("Config missing required key: model_routing")
    rprint(f"Config validation passed: {path}")


@run_app.command("status")
def run_status(run_id: str = typer.Argument("latest")) -> None:
    """Show status for a run."""
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    status = control.get_status(resolved)
    rprint(f"Run {resolved}: {status}")


@run_app.command("wait")
def run_wait(
    run_id: str = typer.Argument("latest"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Maximum wait time in seconds"),
) -> None:
    """Block until a run is complete."""
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    status = control.wait_for_status(
        resolved,
        target_statuses={"stopped", "completed", "failed"},
        timeout_seconds=float(timeout),
    )
    rprint(f"Run {resolved} reached terminal status: {status}")


@run_app.command("events")
def run_events(run_id: str = typer.Argument("latest")) -> None:
    """Stream events for a run."""
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    events = control.get_events(resolved)
    if not events:
        rprint(f"No events found for run {resolved}.")
        return
    for event in events:
        payload = json.dumps(event.payload, sort_keys=True)
        rprint(f"{event.timestamp} {event.event_type} {payload}")


@run_app.command("stop")
def run_stop(run_id: str) -> None:
    """Stop a campaign run."""
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    control.stop_run(resolved, reason="cli stop command")
    rprint(f"Run {resolved} stopped.")


@run_app.command("resume")
def run_resume(run_id: str) -> None:
    """Resume a campaign run from checkpoint."""
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    control.resume_run(resolved)
    rprint(f"Run {resolved} resumed.")


@pack_app.command("install")
def pack_install(source: str) -> None:
    """Install a campaign pack from a path or git URL."""
    if source.startswith("http://") or source.startswith("https://"):
        rprint(f"Remote install placeholder (manual clone required): {source}")
        return
    source_path = Path(source).resolve()
    if not source_path.exists():
        raise typer.BadParameter(f"Pack source does not exist: {source_path}")
    if source_path.is_file():
        source_path = source_path.parent
    if not (source_path / "campaign.yaml").exists():
        raise typer.BadParameter("Pack source must contain campaign.yaml")
    destination_root = Path("campaign-packs")
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source_path.name
    shutil.copytree(source_path, destination, dirs_exist_ok=True)
    rprint(f"Installed campaign pack to {destination}")


@pack_app.command("list")
def pack_list(
    packs_root: Path = typer.Option(Path("campaign-packs"), "--packs-root"),
) -> None:
    """List available campaign packs."""
    loader = CampaignConfigLoader(packs_root)
    packs = loader.discover_packs()
    if not packs:
        rprint("No campaign packs discovered.")
        return
    for name, path in packs.items():
        rprint(f"{name}: {path}")


@approvals_app.command("list")
def approvals_list() -> None:
    """List approval states."""
    actions = _approvals_store().list()
    if not actions:
        rprint("No granted approvals.")
        return
    for action in actions:
        rprint(action)


@approvals_app.command("grant")
def approvals_grant(action: str) -> None:
    """Grant approval for an action."""
    decision = _approvals_store().grant(action)
    rprint(f"Granted approval for action: {decision.action}")


@approvals_app.command("revoke")
def approvals_revoke(action: str) -> None:
    """Revoke approval for an action."""
    decision = _approvals_store().revoke(action)
    rprint(f"Revoked approval for action: {decision.action}")


@approvals_app.command("reset")
def approvals_reset() -> None:
    """Reset approvals to default empty state."""
    _approvals_store().reset()
    rprint("Approvals reset.")


@context_app.command("report")
def context_report(
    skills_root: Path = typer.Option(
        Path("skills"), "--skills-root", help="Directory root containing SKILL.md files"
    ),
    skill: list[str] | None = typer.Option(
        None, "--skill", "-s", help="Skill name(s) to include; defaults to all discovered"
    ),
    max_chars_per_file: int = typer.Option(4000, "--max-per-file"),
    max_total_chars: int = typer.Option(12000, "--max-total"),
) -> None:
    """Report bounded context assembly for selected skills."""
    registry = SkillRegistry(
        [skills_root],
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
    )
    discovered = registry.discover_skills()
    if not discovered:
        rprint(f"No skills discovered under {skills_root}")
        return

    selected = skill or sorted(discovered.keys())
    bundle = registry.build_context(selected)
    rprint(f"Selected skills: {', '.join(selected)}")
    rprint(f"Included files: {len(bundle.report.included_files)}")
    rprint(f"Omitted files: {len(bundle.report.omitted_files)}")
    rprint(f"Truncated files: {len(bundle.report.truncated_files)}")
    rprint(
        f"Total chars: {bundle.report.total_chars}/{bundle.report.max_total_chars}"
    )


@latex_app.command("skeleton")
def latex_skeleton(
    title: str = typer.Option(..., "--title"),
    author: str = typer.Option(..., "--author"),
    abstract: str = typer.Option(..., "--abstract"),
    output: Path = typer.Option(Path("paper.tex"), "--output", "-o"),
) -> None:
    """Generate a preprint skeleton .tex file."""
    toolchain = LatexToolchain()
    path = toolchain.generate_skeleton(
        title=title,
        author=author,
        abstract=abstract,
        output_file=output,
    )
    rprint(f"Generated LaTeX skeleton: {path}")


@latex_app.command("build")
@latex_app.command("compile")
def latex_compile(
    tex_file: Path = typer.Argument(..., exists=True, readable=True),
    timeout: int = typer.Option(120, "--timeout", "-t"),
) -> None:
    """Compile a .tex file to PDF using latexmk."""
    toolchain = LatexToolchain()
    result = toolchain.compile(tex_file, timeout_seconds=float(timeout))
    if not result.success:
        rprint("LaTeX compile failed.")
        if result.stderr:
            rprint(result.stderr)
        raise typer.Exit(code=1)
    rprint(f"Compiled PDF: {result.pdf_path}")


@latex_app.command("clean")
def latex_clean(
    tex_file: Path = typer.Argument(..., exists=True, readable=True),
    timeout: int = typer.Option(60, "--timeout", "-t"),
) -> None:
    """Clean LaTeX auxiliary build files."""
    toolchain = LatexToolchain()
    success = toolchain.clean(tex_file, timeout_seconds=float(timeout))
    if not success:
        rprint("LaTeX clean failed.")
        raise typer.Exit(code=1)
    rprint(f"Cleaned auxiliary files for {tex_file}")


@latex_app.command("bibgen")
def latex_bibgen(
    entries_json: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("references.bib"), "--output", "-o"),
) -> None:
    """Generate BibTeX from JSON list of entries."""
    payload = json.loads(entries_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise typer.BadParameter("entries_json must contain a JSON list")
    toolchain = LatexToolchain()
    entries = toolchain.entries_from_payload(payload)
    out_path = toolchain.generate_bibtex(entries, output_file=output)
    rprint(f"Generated BibTeX file: {out_path}")


@sandbox_app.command("explain")
def sandbox_explain(message: str = typer.Argument("")) -> None:
    """Explain likely reasons a sandboxed action was blocked."""
    msg = message.lower()
    if "import os" in msg or "subprocess" in msg:
        rprint("Blocked because subprocess/system-level imports are disallowed in sandbox mode.")
        return
    if "network" in msg or "socket" in msg:
        rprint("Blocked because outbound network access is disabled for the sandbox.")
        return
    if message:
        rprint(f"Sandbox block hint: {message}")
        return
    rprint("Provide an error message to diagnose sandbox policy blocks.")


@campaign_app.command("clean")
def campaign_clean(
    run_id: str | None = typer.Option(None, "--run-id", help="Optional run id for partial cleanup"),
    yes: bool = typer.Option(False, "--yes", help="Confirm destructive cleanup"),
) -> None:
    """Clean campaign data for isolation and reproducibility."""
    if not yes:
        raise typer.BadParameter("Pass --yes to confirm campaign cleanup.")

    root = Path(".openeinstein")
    if not root.exists():
        rprint("No .openeinstein directory found.")
        return

    if run_id is None:
        shutil.rmtree(root)
        rprint("Removed .openeinstein workspace data.")
        return

    removed_any = False
    for path in [
        root / "artifacts" / run_id,
        root / "control-plane" / "runs" / f"{run_id}.json",
        root / "control-plane" / "events" / f"{run_id}.jsonl",
    ]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed_any = True
    if removed_any:
        rprint(f"Removed run-scoped files for {run_id}.")
    else:
        rprint(f"No run-scoped files found for {run_id}.")


@report_app.command("generate")
def report_generate(
    run_id: str = typer.Argument("latest"),
    output: Path = typer.Option(Path("campaign-report.md"), "--output", "-o"),
    latex_output: Path | None = typer.Option(
        None,
        "--latex-output",
        help="Optional .tex export path",
    ),
) -> None:
    """Generate a campaign report from persisted run data."""
    db = CampaignDB(_db_path())
    control = _control_plane()
    resolved = _resolve_run_id(control, run_id)
    generator = CampaignReportGenerator(db)
    report = generator.synthesize(resolved)
    markdown_path = generator.write_markdown(report, output)
    rprint(f"Generated report: {markdown_path}")
    if latex_output is not None:
        latex_path = generator.export_latex(report, latex_output)
        rprint(f"Generated LaTeX report: {latex_path}")
    db.close()


def _db_path() -> Path:
    return Path(".openeinstein") / "openeinstein.db"


def _approvals_store() -> ApprovalsStore:
    return ApprovalsStore(Path(".openeinstein") / "approvals.json")


def _control_plane() -> FileBackedControlPlane:
    return FileBackedControlPlane(Path(".openeinstein") / "control-plane")


def _resolve_run_id(control: FileBackedControlPlane, run_id: str) -> str:
    if run_id != "latest":
        return run_id
    latest = control.latest_run_id()
    if latest is None:
        raise typer.BadParameter("No runs found.")
    return latest


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
