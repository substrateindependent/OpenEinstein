"""Executor-backed control-plane adapter used for production runtime cutover."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from openeinstein.campaigns.executor import CampaignExecutor, RuntimeLimits
from openeinstein.gateway.control_plane import (
    ArtifactRecord,
    RunEvent,
    RunRecord,
    RunStatus,
    FileBackedControlPlane,
)
from openeinstein.tools import ToolBus, ToolRuntimeInitReport, initialize_tool_bus_from_config


class ExecutorBackedControlPlane:
    """Compatibility adapter exposing ControlPlane APIs over CampaignExecutor."""

    def __init__(
        self,
        root: str | Path = Path(".openeinstein") / "control-plane",
        db_path: str | Path = Path(".openeinstein") / "openeinstein.db",
        config_path: str | Path = Path("configs") / "openeinstein.example.yaml",
        runtime_limits: RuntimeLimits | None = None,
    ) -> None:
        self._compat = FileBackedControlPlane(root)
        self._tool_bus, self._tool_report = initialize_tool_bus_from_config(
            config_path,
            workspace_root=Path(db_path).parent,
            db_path=db_path,
        )
        executor_kwargs: dict[str, Any] = {"db_path": db_path, "tool_bus": self._tool_bus}
        if runtime_limits is not None:
            executor_kwargs["runtime_limits"] = runtime_limits
        self._executor = CampaignExecutor(**executor_kwargs)
        self._synced_seq: dict[str, int] = {}

    @property
    def tool_bus(self) -> ToolBus:
        return self._tool_bus

    @property
    def tool_report(self) -> ToolRuntimeInitReport:
        return self._tool_report

    def issue_run_id(self) -> str:
        return self._executor.issue_run_id()

    def latest_run_id(self) -> str | None:
        runs = self._executor.list_runs()
        if runs:
            runs.sort(key=lambda item: item.updated_at)
            return runs[-1].run_id
        return self._compat.latest_run_id()

    def start_run(
        self,
        run_id: str | None = None,
        campaign_path: str | Path | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        resolved_campaign = campaign_path or _default_campaign_path()
        try:
            started = self._executor.start_campaign(
                run_id=run_id,
                campaign_path=resolved_campaign,
                parameters=parameters,
            )
        except Exception:  # noqa: BLE001
            # Preserve legacy behavior for loose/invalid campaign manifests.
            started = self._executor.start_campaign(
                run_id=run_id,
                campaign_path=_default_campaign_path(),
                parameters={**(parameters or {}), "requested_campaign_path": str(resolved_campaign)},
            )
        # Keep JSONL compatibility for legacy tooling/tests.
        if started not in {record.run_id for record in self._compat.list_runs()}:
            self._compat.start_run(started)
        if campaign_path:
            self._compat.emit_event(started, "campaign_path_set", {"campaign_path": str(campaign_path)})
        self._sync_runtime_events(started)
        return started

    def emit_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> RunEvent:
        event = self._compat.emit_event(run_id, event_type, payload)
        return event

    def get_events(self, run_id: str) -> list[RunEvent]:
        self._sync_runtime_events(run_id)
        return self._compat.get_events(run_id)

    def get_status(self, run_id: str) -> RunStatus:
        try:
            runtime_run = self._executor.get_run(run_id)
        except KeyError:
            return self._compat.get_status(run_id)
        status = runtime_run.status
        if runtime_run.desired_state in {"stopped", "paused"} and status not in {
            "stopped",
            "completed",
            "failed",
        }:
            return "stopped"
        if status in {"queued", "planning", "generating", "gating", "literature", "verifying"}:
            return "running"
        if status == "paused":
            return "stopped"
        if status == "stopped":
            return "stopped"
        if status == "completed":
            return "completed"
        if status == "failed":
            return "failed"
        return "running"

    def list_runs(self) -> list[RunRecord]:
        records: list[RunRecord] = []
        runtime_ids: set[str] = set()
        for run in self._executor.list_runs():
            runtime_ids.add(run.run_id)
            records.append(
                RunRecord(
                    run_id=run.run_id,
                    status=self.get_status(run.run_id),
                    started_at=run.created_at,
                    updated_at=run.updated_at,
                    artifacts=self._compat.list_artifacts(run.run_id),
                )
            )
        for record in self._compat.list_runs():
            if record.run_id in runtime_ids:
                continue
            records.append(record)
        records.sort(key=lambda item: item.updated_at)
        return records

    def get_run(self, run_id: str) -> RunRecord:
        try:
            run = self._executor.get_run(run_id)
            return RunRecord(
                run_id=run_id,
                status=self.get_status(run_id),
                started_at=run.created_at,
                updated_at=run.updated_at,
                artifacts=self._compat.list_artifacts(run_id),
            )
        except KeyError:
            return self._compat.get_run(run_id)

    def stop_run(self, run_id: str, reason: str | None = None) -> None:
        runtime_known = True
        try:
            self._executor.stop_campaign(run_id, reason)
        except KeyError:
            runtime_known = False
        if runtime_known:
            self._ensure_compat_run(run_id)
        self._compat.stop_run(run_id, reason=reason)

    def resume_run(self, run_id: str) -> None:
        runtime_known = True
        try:
            self._executor.resume_campaign(run_id)
        except KeyError:
            runtime_known = False
        if runtime_known:
            self._ensure_compat_run(run_id)
        self._compat.resume_run(run_id)

    def wait_for_status(
        self,
        run_id: str,
        target_statuses: set[RunStatus],
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.1,
    ) -> RunStatus:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() <= deadline:
            status = self.get_status(run_id)
            if status in target_statuses:
                return status
            time.sleep(poll_interval_seconds)
        raise TimeoutError(
            f"Timed out waiting for run {run_id} to reach {sorted(target_statuses)}"
        )

    def attach_artifact(self, run_id: str, name: str, source_path: str | Path) -> ArtifactRecord:
        if run_id not in {record.run_id for record in self._compat.list_runs()}:
            self._compat.start_run(run_id)
        return self._compat.attach_artifact(run_id, name, source_path)

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        return self._compat.list_artifacts(run_id)

    def get_lane_status(self) -> dict[str, dict[str, Any]]:
        """Return per-lane status from executor (empty dict if no lanes configured)."""
        return self._executor.get_lane_status()

    def _ensure_compat_run(self, run_id: str) -> None:
        try:
            self._compat.get_run(run_id)
        except KeyError:
            self._compat.start_run(run_id)

    def _sync_runtime_events(self, run_id: str) -> None:
        if run_id not in self._synced_seq:
            existing = self._compat.get_events(run_id)
            observed_seq = 0
            for existing_event in existing:
                value = existing_event.payload.get("seq")
                if isinstance(value, int):
                    observed_seq = max(observed_seq, value)
            self._synced_seq[run_id] = observed_seq

        after_seq = self._synced_seq.get(run_id, 0)
        try:
            runtime_events = self._executor.get_events(run_id, after_seq=after_seq, limit=10_000)
        except KeyError:
            # Legacy file-backed runs have no executor state; keep compatibility events only.
            return
        self._ensure_compat_run(run_id)
        for runtime_event in runtime_events:
            payload = dict(runtime_event.payload)
            payload.setdefault("seq", runtime_event.seq)
            if runtime_event.step_id is not None:
                payload.setdefault("step_id", runtime_event.step_id)
            self._compat.emit_event(run_id, runtime_event.event_type, payload)
            self._synced_seq[run_id] = runtime_event.seq



def _default_campaign_path() -> Path:
    path = Path("campaign-packs") / "modified-gravity-action-search" / "campaign.yaml"
    if path.exists():
        return path

    fallback = Path(".openeinstein") / "default-campaign.yaml"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    if not fallback.exists():
        fallback.write_text(
            "\n".join(
                [
                    "campaign:",
                    "  name: default-runtime-campaign",
                    "  version: '0.1.0'",
                    "  description: auto-generated fallback campaign",
                    "  search_space:",
                    "    generator_skill: fallback-skill",
                    "  dependencies:",
                    "    tools: []",
                    "  gate_pipeline:",
                    "    - name: fallback-gate",
                    "      skill: fallback-gate",
                    "      cas_requirements: []",
                    "      timeout_seconds: 5",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return fallback
