"""Computation-focused agent with template filling and gated CAS execution."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable

from pydantic import BaseModel, Field

from openeinstein.agents.base import OpenEinsteinAgent
from openeinstein.tools import ToolResult


class GateResult(BaseModel):
    name: str
    passed: bool
    reason: str


class ComputationRunResult(BaseModel):
    success: bool
    rendered_expression: str
    selected_server: str
    tool_result: dict[str, Any] = Field(default_factory=dict)
    gates: list[GateResult] = Field(default_factory=list)
    error: str | None = None


GateFn = Callable[[dict[str, Any]], GateResult]


class ComputationAgent(OpenEinsteinAgent):
    """Agent for deterministic template -> CAS -> deterministic gates."""

    _TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

    def __init__(
        self,
        *,
        cas_server: str,
        cas_tool: str,
        gate_sequence: list[GateFn],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._cas_server = cas_server
        self._cas_tool = cas_tool
        self._gate_sequence = gate_sequence

    def run(
        self,
        prompt: str,  # noqa: ARG002
        **kwargs: Any,
    ) -> dict[str, Any]:
        template = str(kwargs["template"])
        variables = dict(kwargs.get("variables", {}))
        timeout_seconds = float(kwargs.get("timeout_seconds", 10.0))
        fallback_server = kwargs.get("fallback_server")
        run_id = kwargs.get("run_id")

        rendered = self.render_template(template, variables)
        args = {"expression": rendered}

        primary = self._call_with_timeout(
            server=self._cas_server,
            tool=self._cas_tool,
            args=args,
            run_id=run_id,
            timeout_seconds=timeout_seconds,
        )
        selected_server = self._cas_server
        active_result = primary

        if not primary.success and fallback_server:
            fallback = self._call_with_timeout(
                server=str(fallback_server),
                tool=self._cas_tool,
                args=args,
                run_id=run_id,
                timeout_seconds=timeout_seconds,
            )
            active_result = fallback
            selected_server = str(fallback_server)

        if not active_result.success:
            return ComputationRunResult(
                success=False,
                rendered_expression=rendered,
                selected_server=selected_server,
                error=active_result.error or "CAS call failed",
            ).model_dump()

        payload = active_result.output if isinstance(active_result.output, dict) else {}
        gate_results = [gate(payload) for gate in self._gate_sequence]
        if any(not gate.passed for gate in gate_results):
            failed_gate = [gate for gate in gate_results if not gate.passed][0]
            return ComputationRunResult(
                success=False,
                rendered_expression=rendered,
                selected_server=selected_server,
                tool_result=payload,
                gates=gate_results,
                error=f"Gate failed: {failed_gate.name} ({failed_gate.reason})",
            ).model_dump()

        return ComputationRunResult(
            success=True,
            rendered_expression=rendered,
            selected_server=selected_server,
            tool_result=payload,
            gates=gate_results,
        ).model_dump()

    @classmethod
    def render_template(cls, template: str, variables: dict[str, Any]) -> str:
        missing: list[str] = []

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                missing.append(key)
                return match.group(0)
            return str(variables[key])

        rendered = cls._TEMPLATE_PATTERN.sub(replace, template)
        if missing:
            raise KeyError(f"Missing template variables: {', '.join(sorted(set(missing)))}")
        return rendered

    def _call_with_timeout(
        self,
        *,
        server: str,
        tool: str,
        args: dict[str, Any],
        run_id: str | None,
        timeout_seconds: float,
    ) -> ToolResult:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._tool_bus.call, server, tool, args, run_id)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError:
                return ToolResult(success=False, error=f"Timed out after {timeout_seconds}s")
