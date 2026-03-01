"""Agent orchestration primitives with delegation and compaction."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from openeinstein.agents.base import OpenEinsteinAgent


class DelegatedTask(BaseModel):
    task_id: str
    agent_name: str
    prompt: str
    priority: int = 0


class TaskResult(BaseModel):
    task_id: str
    agent_name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class OrchestrationSummary(BaseModel):
    execution_order: list[str] = Field(default_factory=list)
    results: list[TaskResult] = Field(default_factory=list)
    aggregated_output: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AdaptiveScheduler(Protocol):
    def order(
        self, tasks: list[DelegatedTask], failure_scores: dict[str, int]
    ) -> list[DelegatedTask]: ...


class DefaultAdaptiveScheduler:
    """Sorts tasks by failure score then declared priority."""

    def order(
        self, tasks: list[DelegatedTask], failure_scores: dict[str, int]
    ) -> list[DelegatedTask]:
        return sorted(
            tasks,
            key=lambda task: (failure_scores.get(task.task_id, 0), task.priority, task.task_id),
        )


class AgentOrchestrator:
    """Delegates tasks to sub-agents and aggregates outputs."""

    def __init__(
        self,
        subagents: dict[str, OpenEinsteinAgent],
        *,
        scheduler: AdaptiveScheduler | None = None,
        invariants: list[str] | None = None,
        max_compacted_chars: int = 1200,
    ) -> None:
        self._subagents = subagents
        self._scheduler = scheduler or DefaultAdaptiveScheduler()
        self._invariants = invariants or []
        self._max_compacted_chars = max_compacted_chars

    def execute(
        self,
        tasks: list[DelegatedTask],
        *,
        run_id: str | None = None,
        failure_scores: dict[str, int] | None = None,
    ) -> OrchestrationSummary:
        ordered_tasks = self._scheduler.order(tasks, failure_scores or {})
        results: list[TaskResult] = []
        aggregated: dict[str, dict[str, Any]] = {}
        execution_order: list[str] = []

        for task in ordered_tasks:
            execution_order.append(task.task_id)
            if task.agent_name not in self._subagents:
                result = TaskResult(
                    task_id=task.task_id,
                    agent_name=task.agent_name,
                    success=False,
                    error=f"Unknown subagent: {task.agent_name}",
                )
                results.append(result)
                continue

            agent = self._subagents[task.agent_name]
            compacted_prompt = self.compact_with_invariants(task.prompt, self._invariants)
            try:
                output = agent.run(compacted_prompt, run_id=run_id)
                result = TaskResult(
                    task_id=task.task_id,
                    agent_name=task.agent_name,
                    success=True,
                    output=output,
                )
            except Exception as exc:
                result = TaskResult(
                    task_id=task.task_id,
                    agent_name=task.agent_name,
                    success=False,
                    error=str(exc),
                )

            results.append(result)
            if result.success:
                aggregated[result.task_id] = result.output

        return OrchestrationSummary(
            execution_order=execution_order,
            results=results,
            aggregated_output=aggregated,
        )

    def compact_with_invariants(self, text: str, invariants: list[str]) -> str:
        if len(text) <= self._max_compacted_chars and all(token in text for token in invariants):
            return text

        payload = text[: self._max_compacted_chars]
        missing = [token for token in invariants if token not in payload]
        if not missing:
            return payload

        joined = "\n".join(missing)
        reserve = len(joined) + 2
        head_limit = max(0, self._max_compacted_chars - reserve)
        compacted = payload[:head_limit]
        return f"{compacted}\n{joined}"
