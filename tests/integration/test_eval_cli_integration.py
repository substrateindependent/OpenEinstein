"""Integration tests for eval CLI commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openeinstein.cli.main import app


def test_eval_cli_list_run_results(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    suite_dir = tmp_path / "evals"
    suite_dir.mkdir()
    suite_path = suite_dir / "trivial.yaml"
    suite_path.write_text(
        """
eval_suite:
  name: cli-suite
  cases:
    - name: alpha
      input:
        payload: a
      expected:
        payload: a
    - name: beta
      input:
        payload: b
      expected:
        payload: b
""".strip()
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    listed = runner.invoke(app, ["eval", "list", "--path", str(suite_dir)])
    assert listed.exit_code == 0
    assert "cli-suite" in listed.stdout

    run = runner.invoke(
        app, ["eval", "run", str(suite_path), "--run-id", "eval-cli-run-1"]
    )
    assert run.exit_code == 0
    assert "2/2 passed" in run.stdout

    results = runner.invoke(app, ["eval", "results", "eval-cli-run-1"])
    assert results.exit_code == 0
    assert "2/2 passed" in results.stdout
    assert "cli-suite/alpha: PASS" in results.stdout
