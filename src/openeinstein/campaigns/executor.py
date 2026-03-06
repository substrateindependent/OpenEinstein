"""Production campaign executor with durable state, steps, and replayable events."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from openeinstein.campaigns.config import CampaignConfigLoader, CampaignDefinition
from openeinstein.campaigns.lanes import LaneRegistry
from openeinstein.gateway.policy import PolicyConfig, PolicyInvariants, load_policy
from openeinstein.persistence import (
    CampaignDB,
    RuntimeEventRecord,
    RuntimeRunRecord,
    RuntimeStepRecord,
)
from openeinstein.routing import ModelRouter, RoutingConfig
from openeinstein.routing.models import (
    ModelConfig,
    RoleConfig,
    RoutingRoot,
    RoutingRoles,
    UsageRecord,
)
from openeinstein.security import (
    ApprovalRequiredError,
    ApprovalsStore,
    PolicyEngine,
    PolicyViolationError,
)
from openeinstein.tools import ToolBus

if TYPE_CHECKING:
    from openeinstein.agents.harness import RuntimeHarness
    from openeinstein.agents.memory_flush import MemoryFlushManager
    from openeinstein.campaigns.queue_modes import QueueModeHandler
    from openeinstein.campaigns.state import ConcurrentStepTracker
    from openeinstein.gateway.hooks import HookRegistry
    from openeinstein.security.sandbox import SessionSandbox

ExecutorStatus = Literal[
    "queued",
    "planning",
    "generating",
    "gating",
    "literature",
    "verifying",
    "paused",
    "stopped",
    "completed",
    "failed",
]

_STEP_PHASES: list[ExecutorStatus] = [
    "planning",
    "generating",
    "gating",
    "literature",
    "verifying",
]
_TERMINAL_STATES: set[ExecutorStatus] = {"completed", "failed", "stopped"}


class RuntimeLimits(BaseModel):
    max_steps: int = Field(default=20, ge=1)
    max_runtime_minutes: int = Field(default=60, ge=1)
    max_cost_usd: float = Field(default=25.0, ge=0)
    max_tokens: int = Field(default=100_000, ge=1)
    parallel_lanes: int | None = Field(default=None, ge=1)


class ExecutorRun(BaseModel):
    run_id: str
    campaign_path: str
    status: ExecutorStatus
    desired_state: str
    replay_cursor: int
    current_step_index: int
    max_steps: int
    max_runtime_minutes: int
    max_cost_usd: float
    max_tokens: int
    parameters: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str
    updated_at: str


class ExecutorStep(BaseModel):
    step_id: str
    run_id: str
    step_index: int
    phase: str
    status: str
    attempt: int
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    error: str | None = None
    started_at: str
    ended_at: str | None = None


class ExecutorEvent(BaseModel):
    run_id: str
    seq: int
    event_type: str
    step_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class CampaignExecutor:
    """Durable campaign runtime service used by CLI/API v2 surfaces."""

    def __init__(
        self,
        *,
        db_path: str | Path,
        runtime_limits: RuntimeLimits | None = None,
        model_router: ModelRouter | None = None,
        tool_bus: ToolBus | None = None,
        approvals_store: ApprovalsStore | None = None,
        policy_engine: PolicyEngine | None = None,
        policy_path: str | Path = Path("configs") / "POLICY.json",
        lane_registry: LaneRegistry | None = None,
        concurrent_tracker: ConcurrentStepTracker | None = None,
        hook_registry: HookRegistry | None = None,
        runtime_harness: RuntimeHarness | None = None,
        sandbox_base_dir: Path | None = None,
        queue_mode_handler: QueueModeHandler | None = None,
        memory_flush_manager: MemoryFlushManager | None = None,
    ) -> None:
        self._db = CampaignDB(db_path)
        self._db_path = Path(db_path)
        self._runtime_limits = runtime_limits or RuntimeLimits()
        self._model_router = model_router or _fallback_router()
        self._tool_bus = tool_bus
        workspace_root = self._db_path.parent
        self._approvals = approvals_store or ApprovalsStore(workspace_root / "approvals.json")
        self._policy_engine = policy_engine or PolicyEngine(
            _load_policy_with_fallback(policy_path),
            self._approvals,
        )
        self._workers: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        # Auto-create lane registry from parallel_lanes if no explicit registry
        if lane_registry is not None:
            self._lane_registry: LaneRegistry | None = lane_registry
        elif self._runtime_limits.parallel_lanes is not None:
            from openeinstein.campaigns.lanes import LaneConfig as _LaneConfig

            self._lane_registry = LaneRegistry(
                {
                    "main": _LaneConfig(
                        name="main",
                        max_concurrent=self._runtime_limits.parallel_lanes,
                    ),
                }
            )
        else:
            self._lane_registry = None
        self._concurrent_tracker = concurrent_tracker
        self._hook_registry = hook_registry
        self._runtime_harness = runtime_harness
        self._sandbox_base_dir = sandbox_base_dir
        if queue_mode_handler is None:
            from openeinstein.campaigns.queue_modes import QueueModeHandler as _QMH

            self._queue_mode_handler: QueueModeHandler = _QMH()
        else:
            self._queue_mode_handler = queue_mode_handler
        self._memory_flush_manager = memory_flush_manager
        self._active_sandboxes: dict[str, SessionSandbox] = {}

    def _dispatch_hook(self, hook_point: str, payload: dict[str, Any], run_id: str | None = None) -> None:
        """Dispatch a hook if registry is configured. Errors are logged, not raised."""
        if self._hook_registry is None:
            return
        try:
            from openeinstein.gateway.hooks import HookContext

            ctx = HookContext(hook_point=hook_point, run_id=run_id, payload=payload)  # type: ignore[arg-type]
            self._hook_registry.dispatch(hook_point, ctx)  # type: ignore[arg-type]
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Hook dispatch error for %s", hook_point)

    def start_campaign(
        self,
        *,
        campaign_path: str | Path,
        parameters: dict[str, Any] | None = None,
        run_id: str | None = None,
        auto_run: bool = True,
    ) -> str:
        resolved_path = str(Path(campaign_path).resolve())
        parsed = CampaignConfigLoader.load_config(campaign_path)
        created_run_id = run_id or self.issue_run_id()

        with self._lock:
            self._db.create_runtime_run(
                run_id=created_run_id,
                campaign_path=resolved_path,
                status="queued",
                desired_state="running",
                max_steps=self._runtime_limits.max_steps,
                max_runtime_minutes=self._runtime_limits.max_runtime_minutes,
                max_cost_usd=self._runtime_limits.max_cost_usd,
                max_tokens=self._runtime_limits.max_tokens,
                parameters={"campaign_name": parsed.name, **(parameters or {})},
            )
            self._db.append_runtime_event(
                created_run_id,
                event_type="run_queued",
                payload={"campaign_path": resolved_path},
            )

        # Create session sandbox if sandbox_base_dir is configured
        if self._sandbox_base_dir is not None:
            from openeinstein.security.sandbox import (
                ScopedApprovalsStore as _SAS,
                SessionSandbox as _SB,
            )

            sandbox = _SB(run_id=created_run_id, base_dir=self._sandbox_base_dir)
            self._active_sandboxes[created_run_id] = sandbox
            # Create scoped approvals so grants in one run don't leak to another
            self._scoped_approvals = _SAS(self._approvals, run_id=created_run_id)

        # Initialize runtime harness if configured
        if self._runtime_harness is not None:
            self._runtime_harness.initialize({
                "run_id": created_run_id,
                "campaign_path": resolved_path,
                "parameters": parameters or {},
            })

        if auto_run:
            self._spawn_worker(created_run_id, parsed)
        return created_run_id

    def resume_campaign(self, run_id: str) -> None:
        run = self._require_run(run_id)
        if run.status in {"completed", "failed"}:
            return
        with self._lock:
            self._db.update_runtime_run_state(
                run_id,
                status="queued" if run.status in {"paused", "stopped"} else run.status,
                desired_state="running",
            )
            self._db.append_runtime_event(run_id, event_type="run_resume_requested", payload={})

        config = CampaignConfigLoader.load_config(run.campaign_path)
        self._spawn_worker(run_id, config)

    def pause_campaign(self, run_id: str) -> None:
        self._require_run(run_id)
        with self._lock:
            self._db.update_runtime_run_state(run_id, desired_state="paused")
            self._db.append_runtime_event(run_id, event_type="run_pause_requested", payload={})

    def stop_campaign(self, run_id: str, reason: str | None = None) -> None:
        self._require_run(run_id)
        with self._lock:
            self._db.update_runtime_run_state(run_id, desired_state="stopped")
            self._db.append_runtime_event(
                run_id,
                event_type="run_stop_requested",
                payload={"reason": reason or ""},
            )

    def execute_next_step(self, run_id: str) -> ExecutorStep | None:
        run = self._require_run(run_id)
        if run.status in _TERMINAL_STATES:
            return None
        config = CampaignConfigLoader.load_config(run.campaign_path)
        executed = self._execute_single_step(run_id, config)
        if executed is not None:
            return executed
        return None

    def wait_for_status(
        self,
        run_id: str,
        target_statuses: set[str],
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.1,
    ) -> str:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() <= deadline:
            status = self.get_run(run_id).status
            if status in target_statuses:
                return status
            time.sleep(poll_interval_seconds)
        raise TimeoutError(
            f"Timed out waiting for run {run_id} to reach {sorted(target_statuses)}"
        )

    def get_run(self, run_id: str) -> ExecutorRun:
        with self._lock:
            run = self._require_run(run_id)
            return _runtime_run_to_model(run)

    def list_runs(self) -> list[ExecutorRun]:
        with self._lock:
            return [_runtime_run_to_model(run) for run in self._db.list_runtime_runs()]

    def get_steps(self, run_id: str) -> list[ExecutorStep]:
        with self._lock:
            self._require_run(run_id)
            return [_runtime_step_to_model(step) for step in self._db.list_runtime_steps(run_id)]

    def get_events(self, run_id: str, after_seq: int = 0, limit: int = 100) -> list[ExecutorEvent]:
        with self._lock:
            self._require_run(run_id)
            rows = self._db.get_runtime_events(run_id, after_seq=after_seq, limit=limit)
            return [_runtime_event_to_model(row) for row in rows]

    @staticmethod
    def issue_run_id() -> str:
        return f"run-{uuid.uuid4().hex[:12]}"

    def get_lane_status(self) -> dict[str, dict[str, Any]]:
        """Return per-lane status with active counts and max concurrency."""
        if self._lane_registry is None:
            return {}
        raw = self._lane_registry.lane_status()
        result: dict[str, dict[str, Any]] = {}
        for lane_name in self._lane_registry.lane_names:
            lane_info = raw.get(lane_name, {})
            result[lane_name] = {
                "active": lane_info.get("active", 0),
                "max": lane_info.get("max_concurrent", 0),
            }
        return result

    def handle_mid_run_message(
        self,
        run_id: str,
        message: str,
        pending_messages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Process a mid-run message through the configured queue mode handler.

        Returns the ``QueueAction`` as a dict.
        """
        from openeinstein.campaigns.lanes import QueueMode

        run = self._require_run(run_id)
        mode_str = run.parameters.get("queue_mode", "followup")
        try:
            mode = QueueMode(mode_str)
        except ValueError:
            mode = QueueMode.FOLLOWUP
        action = self._queue_mode_handler.handle_message(
            mode, pending_messages or [], message,
        )
        return action.model_dump()

    def close(self) -> None:
        self._db.close()

    def _spawn_worker(self, run_id: str, config: CampaignDefinition) -> None:
        existing = self._workers.get(run_id)
        if existing is not None and existing.is_alive():
            return

        worker = threading.Thread(
            target=self._execute_loop,
            args=(run_id, config),
            daemon=True,
            name=f"campaign-exec-{run_id}",
        )
        self._workers[run_id] = worker
        worker.start()

    def _execute_loop(self, run_id: str, config: CampaignDefinition) -> None:
        try:
            self._execute_loop_inner(run_id, config)
        finally:
            self._cleanup_sandbox(run_id)

    def _cleanup_sandbox(self, run_id: str) -> None:
        """Clean up session sandbox and runtime harness for a run.  Errors are logged, not raised."""
        sandbox = self._active_sandboxes.pop(run_id, None)
        if sandbox is not None:
            try:
                sandbox.cleanup()
            except Exception:
                import logging

                logging.getLogger(__name__).exception("Sandbox cleanup error for %s", run_id)
        # Clean up runtime harness
        if self._runtime_harness is not None:
            try:
                self._runtime_harness.cleanup()
            except Exception:
                import logging

                logging.getLogger(__name__).exception("Harness cleanup error for %s", run_id)

    def _execute_loop_inner(self, run_id: str, config: CampaignDefinition) -> None:
        while True:
            run = self._require_run(run_id)
            if run.status in _TERMINAL_STATES:
                return

            if run.desired_state == "stopped":
                with self._lock:
                    self._db.update_runtime_run_state(run_id, status="stopped")
                    self._db.append_runtime_event(run_id, event_type="run_stopped", payload={})
                return

            if run.desired_state == "paused":
                with self._lock:
                    self._db.update_runtime_run_state(run_id, status="paused")
                    self._db.append_runtime_event(run_id, event_type="run_paused", payload={})
                return

            step = self._execute_single_step(run_id, config)
            if step is None:
                return

    def _execute_single_step(self, run_id: str, config: CampaignDefinition) -> ExecutorStep | None:
        run = self._require_run(run_id)
        if run.current_step_index >= len(_STEP_PHASES):
            with self._lock:
                self._db.update_runtime_run_state(run_id, status="completed")
                self._db.append_runtime_event(run_id, event_type="run_completed", payload={})
            return None

        phase = _STEP_PHASES[run.current_step_index]
        step_id = f"step-{run.current_step_index:03d}-{phase}"
        lane_name = _lane_for_phase(phase)

        # Acquire lane semaphore if registry is configured
        if self._lane_registry is not None and lane_name in self._lane_registry.lane_names:
            self._lane_registry.acquire(lane_name)

        try:
            # Re-check desired_state after lane acquisition for interrupt responsiveness
            run = self._require_run(run_id)
            if run.desired_state in ("paused", "stopped"):
                return None

            # Register step in concurrent tracker for phase-level tracking
            if self._concurrent_tracker is not None:
                self._concurrent_tracker.register_step(lane_name, step_id, phase)

            lane_active_count = 0
            if self._lane_registry is not None:
                status = self._lane_registry.lane_status()
                if lane_name in status:
                    lane_active_count = status[lane_name]["active"]

            # Include concurrent tracker status in events (sets → sorted lists for JSON)
            tracker_status: dict[str, Any] = {}
            if self._concurrent_tracker is not None:
                raw = self._concurrent_tracker.lane_status
                tracker_status = {
                    lane: {"active": info["active"], "step_ids": sorted(info["step_ids"])}
                    for lane, info in raw.items()
                }

            with self._lock:
                self._db.update_runtime_run_state(run_id, status=phase)
                self._db.start_runtime_step(
                    run_id=run_id,
                    step_id=step_id,
                    step_index=run.current_step_index,
                    phase=phase,
                    attempt=1,
                    input_payload={"phase": phase, "campaign": config.name},
                )
                self._db.append_runtime_event(
                    run_id,
                    event_type="step_started",
                    step_id=step_id,
                    payload={
                        "phase": phase,
                        "lane_name": lane_name,
                        "lane_active_count": lane_active_count,
                        "tracker_status": tracker_status,
                    },
                )

            precheck = self._deterministic_precheck(run_id)
            reasoning = self._role_routed_reasoning(run_id, phase, config)
            if phase == "literature" and self._require_risky_action(run_id):
                self._policy_engine.enforce_action("network_fetch")

            postcheck = self._deterministic_postcheck(run_id, phase, precheck, reasoning)
            self._apply_phase_side_effects(run_id, phase, postcheck)

            with self._lock:
                self._db.finish_runtime_step(
                    run_id=run_id,
                    step_id=step_id,
                    status="completed",
                    output_payload=postcheck,
                )
                self._db.update_runtime_run_state(
                    run_id,
                    current_step_index=run.current_step_index + 1,
                )
                self._db.append_runtime_event(
                    run_id,
                    event_type="step_completed",
                    step_id=step_id,
                    payload={"phase": phase},
                )
        except (ApprovalRequiredError, PolicyViolationError) as exc:
            with self._lock:
                self._db.finish_runtime_step(
                    run_id=run_id,
                    step_id=step_id,
                    status="failed",
                    error=str(exc),
                    output_payload={"error": str(exc)},
                )
                self._db.update_runtime_run_state(run_id, status="failed", error=str(exc))
                self._db.append_runtime_event(
                    run_id,
                    event_type="policy_blocked",
                    step_id=step_id,
                    payload={"error": str(exc), "phase": phase},
                )
                self._db.append_runtime_event(
                    run_id,
                    event_type="run_failed",
                    payload={"error": str(exc)},
                )
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._db.finish_runtime_step(
                    run_id=run_id,
                    step_id=step_id,
                    status="failed",
                    error=str(exc),
                    output_payload={"error": str(exc)},
                )
                self._db.update_runtime_run_state(run_id, status="failed", error=str(exc))
                self._db.append_runtime_event(
                    run_id,
                    event_type="run_failed",
                    step_id=step_id,
                    payload={"error": str(exc), "phase": phase},
                )
        finally:
            # Always complete step in tracker, including on error
            if self._concurrent_tracker is not None:
                self._concurrent_tracker.complete_step(lane_name, step_id)
            # Always release lane semaphore, including on error
            if self._lane_registry is not None and lane_name in self._lane_registry.lane_names:
                self._lane_registry.release(lane_name)

        latest_step = self._db.get_runtime_step(run_id, step_id)
        if latest_step is None:
            return None
        return _runtime_step_to_model(latest_step)

    def _deterministic_precheck(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._require_run(run_id)
            if run.current_step_index >= run.max_steps:
                raise RuntimeError("max_steps exceeded")
            cost = self._db.get_runtime_cost_totals(run_id)
            if cost["cost_usd"] > run.max_cost_usd:
                raise RuntimeError("max_cost_usd exceeded")
            if cost["prompt_tokens"] + cost["completion_tokens"] > run.max_tokens:
                raise RuntimeError("max_tokens exceeded")
            created_at = _parse_iso(run.created_at)
        elapsed_minutes = (datetime.now(tz=UTC) - created_at).total_seconds() / 60.0
        if elapsed_minutes > run.max_runtime_minutes:
            raise RuntimeError("max_runtime_minutes exceeded")

        # Dispatch budget_warning if token usage exceeds 80% of budget
        tokens_used = cost["prompt_tokens"] + cost["completion_tokens"]
        if run.max_tokens > 0:
            usage_pct = (tokens_used / run.max_tokens) * 100.0
            if usage_pct >= 80.0:
                self._dispatch_hook(
                    "budget_warning",
                    {
                        "tokens_used": tokens_used,
                        "tokens_budget": run.max_tokens,
                        "usage_pct": round(usage_pct, 2),
                        "cost_usd": cost["cost_usd"],
                    },
                    run_id=run_id,
                )
                # Trigger memory flush before compaction at high usage
                if self._memory_flush_manager is not None:
                    try:
                        self._memory_flush_manager.flush_before_compaction(run_id, [])
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception(
                            "Memory flush error for run %s", run_id,
                        )

        return {
            "elapsed_minutes": elapsed_minutes,
            "cost_usd": cost["cost_usd"],
            "tokens": tokens_used,
        }

    def _role_routed_reasoning(
        self,
        run_id: str,
        phase: str,
        config: CampaignDefinition,
    ) -> dict[str, Any]:
        role = _role_for_phase(phase)

        def call(model_config: ModelConfig) -> dict[str, Any]:
            prompt_tokens = 100 + len(phase)
            completion_tokens = 60 + len(config.name)
            cost_usd = 0.0002 * (prompt_tokens + completion_tokens)
            usage = UsageRecord(
                role=role,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
            with self._lock:
                self._model_router.record_usage(usage)
                self._db.add_runtime_usage(
                    run_id=run_id,
                    role=role,
                    provider=model_config.provider,
                    model=model_config.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                )
            return {
                "role": role,
                "provider": model_config.provider,
                "model": model_config.model,
                "phase": phase,
                "uncertainty_note": "Bounded deterministic fallback reasoning path.",
                "citations": [
                    "arXiv:1502.01590",
                    "doi:10.1103/PhysRevD.79.084003",
                ],
            }

        return self._model_router.run_with_fallback(role, call)

    def _deterministic_postcheck(
        self,
        run_id: str,
        phase: str,
        precheck: dict[str, Any],
        reasoning: dict[str, Any],
    ) -> dict[str, Any]:
        required = {"role", "provider", "model", "phase", "uncertainty_note"}
        missing = sorted(required - set(reasoning))
        if missing:
            raise RuntimeError(f"missing reasoning keys: {missing}")

        return {
            "run_id": run_id,
            "phase": phase,
            "precheck": precheck,
            "reasoning": reasoning,
            "postcheck_ok": True,
        }

    def _apply_phase_side_effects(
        self,
        run_id: str,
        phase: str,
        payload: dict[str, Any],
    ) -> None:
        if phase == "generating":
            candidate_key = f"cand-{run_id[:8]}-001"
            with self._lock:
                self._db.add_candidate(
                    run_id,
                    candidate_key,
                    {
                        "phase": phase,
                        "derivation_path": f"artifacts/{run_id}/{candidate_key}.md",
                        "confidence": 0.78,
                    },
                )
                self._db.append_runtime_event(
                    run_id,
                    event_type="candidate_generated",
                    payload={"candidate_key": candidate_key},
                )
            self._dispatch_hook(
                "candidate_generated",
                {"candidate_key": candidate_key, "phase": phase},
                run_id=run_id,
            )
            return

        if phase == "gating":
            with self._lock:
                candidates = self._db.get_candidates(run_id)
                for candidate in candidates:
                    gate_result = {
                        "success": True,
                        "backend": "sympy",
                        "phase": phase,
                    }
                    self._db.update_gate_result(candidate.id, gate_result)
                    # Dispatch gate_passed or gate_failed hook per candidate
                    if gate_result["success"]:
                        self._dispatch_hook(
                            "gate_passed",
                            {"candidate_key": candidate.candidate_key, "backend": "sympy"},
                            run_id=run_id,
                        )
                    else:
                        self._dispatch_hook(
                            "gate_failed",
                            {"candidate_key": candidate.candidate_key, "reason": "gate check failed"},
                            run_id=run_id,
                        )
                if self._require_risky_action(run_id):
                    self._db.log_failure(
                        run_id,
                        "policy",
                        "approval_required",
                        {"phase": phase, "reason": "network_fetch requires approval"},
                    )
            return

        if phase == "literature":
            if self._tool_bus is None or not self._tool_bus.list_servers():
                with self._lock:
                    self._db.append_runtime_event(
                        run_id,
                        event_type="plugin_optional_missing",
                        payload={"component": "literature_connectors", "status": "degraded"},
                    )
                return

            server = self._tool_bus.list_servers()[0]
            tools = self._tool_bus.get_tools(server)
            if tools:
                result = self._tool_bus.call(server, tools[0].name, {}, run_id=run_id)
                with self._lock:
                    self._db.append_runtime_event(
                        run_id,
                        event_type="tool_call",
                        payload={
                            "server": server,
                            "tool": tools[0].name,
                            "success": result.success,
                        },
                    )
            return

        if phase == "verifying":
            with self._lock:
                failures = self._db.get_failure_log(run_id)
                if not failures:
                    self._db.log_failure(
                        run_id,
                        "null-region",
                        "insufficient_evidence",
                        {
                            "phase": phase,
                            "message": "No disqualifying evidence found; default null-result map section inserted",
                        },
                    )

    def _require_risky_action(self, run_id: str) -> bool:
        run = self._require_run(run_id)
        return bool(run.parameters.get("trigger_risky_action", False))

    def _require_run(self, run_id: str) -> RuntimeRunRecord:
        with self._lock:
            run = self._db.get_runtime_run(run_id)
            if run is None:
                raise KeyError(f"Unknown run_id: {run_id}")
            return run



def _fallback_router() -> ModelRouter:
    return ModelRouter(
        RoutingConfig(
            model_routing=RoutingRoot(
                roles=RoutingRoles(
                    reasoning=RoleConfig(
                        description="Fallback reasoning role",
                        default=ModelConfig(provider="fallback", model="reasoning"),
                    ),
                    generation=RoleConfig(
                        description="Fallback generation role",
                        default=ModelConfig(provider="fallback", model="generation"),
                    ),
                    fast=RoleConfig(
                        description="Fallback fast role",
                        default=ModelConfig(provider="fallback", model="fast"),
                    ),
                    embeddings=RoleConfig(
                        description="Fallback embeddings role",
                        default=ModelConfig(provider="fallback", model="embeddings"),
                    ),
                )
            )
        )
    )


def _load_policy_with_fallback(path: str | Path) -> PolicyConfig:
    policy_path = Path(path)
    if policy_path.exists():
        return load_policy(policy_path)
    return PolicyConfig(
        version="fallback-runtime",
        invariants=PolicyInvariants(
            require_approval_for=["network_fetch", "shell_exec", "file_write_outside_workspace"],
            max_llm_calls_per_step=50,
            max_cas_timeout_minutes=60,
            forbidden_operations=["delete_campaign_state"],
            require_verification_after_gates=True,
        ),
        enforced_by="gateway",
        note="Fallback runtime policy",
    )


def _runtime_run_to_model(run: RuntimeRunRecord) -> ExecutorRun:
    return ExecutorRun(
        run_id=run.run_id,
        campaign_path=run.campaign_path,
        status=run.status,  # type: ignore[arg-type]
        desired_state=run.desired_state,
        replay_cursor=run.replay_cursor,
        current_step_index=run.current_step_index,
        max_steps=run.max_steps,
        max_runtime_minutes=run.max_runtime_minutes,
        max_cost_usd=run.max_cost_usd,
        max_tokens=run.max_tokens,
        parameters=run.parameters,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _runtime_step_to_model(step: RuntimeStepRecord) -> ExecutorStep:
    return ExecutorStep(
        step_id=step.step_id,
        run_id=step.run_id,
        step_index=step.step_index,
        phase=step.phase,
        status=step.status,
        attempt=step.attempt,
        input_payload=step.input_payload,
        output_payload=step.output_payload,
        error=step.error,
        started_at=step.started_at,
        ended_at=step.ended_at,
    )


def _runtime_event_to_model(event: RuntimeEventRecord) -> ExecutorEvent:
    return ExecutorEvent(
        run_id=event.run_id,
        seq=event.seq,
        event_type=event.event_type,
        step_id=event.step_id,
        payload=event.payload,
        created_at=event.created_at,
    )


def _lane_for_phase(phase: str) -> str:
    """Map a step phase to the lane name that governs its concurrency."""
    if phase == "literature":
        return "literature"
    return "main"


def _role_for_phase(phase: str) -> Literal["reasoning", "generation", "fast", "embeddings"]:
    if phase in {"planning", "verifying"}:
        return "reasoning"
    if phase in {"generating", "gating"}:
        return "generation"
    if phase == "literature":
        return "fast"
    return "fast"


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)
