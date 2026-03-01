"""Gate pipeline runner with capability-based backend routing."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel

from openeinstein.campaigns.config import GateConfig
from openeinstein.persistence import CampaignDB

GateStatus = Literal["passed", "timeout", "failed"]
FailureType = Literal["missing_capability", "timeout", "execution_error", "gate_failed"]


class GateExecutionResult(BaseModel):
    candidate_key: str
    gate_name: str
    status: GateStatus
    backend: str | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    failure_type: FailureType | None = None


@dataclass(frozen=True)
class CandidateInput:
    candidate_key: str
    data: dict[str, Any]


BackendExecutor = Callable[[str, GateConfig, dict[str, Any]], dict[str, Any]]


class GatePipelineRunner:
    """Runs campaign gates sequentially per candidate with timeout enforcement."""

    def __init__(
        self,
        db: CampaignDB,
        *,
        backend_capabilities: dict[str, set[str]],
        execute_backend: BackendExecutor,
    ) -> None:
        self._db = db
        self._backend_capabilities = backend_capabilities
        self._execute_backend = execute_backend

    def select_backend(self, requirements: list[str]) -> str:
        needed = set(requirements)
        compatible = sorted(
            backend
            for backend, capabilities in self._backend_capabilities.items()
            if needed.issubset(capabilities)
        )
        if not compatible:
            raise ValueError(f"No backend satisfies requirements: {sorted(needed)}")
        return compatible[0]

    def run_candidate(
        self,
        run_id: str,
        candidate: CandidateInput,
        gates: list[GateConfig],
    ) -> list[GateExecutionResult]:
        records = self._db.get_candidates(run_id)
        candidate_row = next((row for row in records if row.candidate_key == candidate.candidate_key), None)
        if candidate_row is None:
            candidate_id = self._db.add_candidate(run_id, candidate.candidate_key, candidate.data)
        else:
            candidate_id = candidate_row.id

        results: list[GateExecutionResult] = []
        for gate in gates:
            try:
                backend = self.select_backend(gate.cas_requirements)
            except ValueError as exc:
                result = GateExecutionResult(
                    candidate_key=candidate.candidate_key,
                    gate_name=gate.name,
                    status="failed",
                    error=str(exc),
                    failure_type="missing_capability",
                )
                self._log_failure(run_id, candidate.candidate_key, result)
                results.append(result)
                break

            try:
                output = self._run_with_timeout(
                    backend=backend,
                    gate=gate,
                    candidate_data=candidate.data,
                    timeout_seconds=gate.timeout_seconds,
                )
            except TimeoutError as exc:
                result = GateExecutionResult(
                    candidate_key=candidate.candidate_key,
                    gate_name=gate.name,
                    status="timeout",
                    backend=backend,
                    error=str(exc),
                    failure_type="timeout",
                )
                self._log_failure(run_id, candidate.candidate_key, result)
                results.append(result)
                break
            except Exception as exc:  # noqa: BLE001
                result = GateExecutionResult(
                    candidate_key=candidate.candidate_key,
                    gate_name=gate.name,
                    status="failed",
                    backend=backend,
                    error=str(exc),
                    failure_type="execution_error",
                )
                self._log_failure(run_id, candidate.candidate_key, result)
                results.append(result)
                break

            if output.get("success") is False:
                result = GateExecutionResult(
                    candidate_key=candidate.candidate_key,
                    gate_name=gate.name,
                    status="failed",
                    backend=backend,
                    output=output,
                    error=str(output.get("error", "gate failed")),
                    failure_type="gate_failed",
                )
                self._db.update_gate_result(candidate_id, output)
                self._log_failure(run_id, candidate.candidate_key, result)
                results.append(result)
                break

            result = GateExecutionResult(
                candidate_key=candidate.candidate_key,
                gate_name=gate.name,
                status="passed",
                backend=backend,
                output=output,
            )
            self._db.update_gate_result(candidate_id, output)
            results.append(result)

        return results

    def run_batch(
        self,
        run_id: str,
        candidates: list[CandidateInput],
        gates: list[GateConfig],
    ) -> dict[str, list[GateExecutionResult]]:
        return {
            candidate.candidate_key: self.run_candidate(run_id, candidate, gates)
            for candidate in candidates
        }

    def _run_with_timeout(
        self,
        *,
        backend: str,
        gate: GateConfig,
        candidate_data: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._execute_backend, backend, gate, candidate_data)
            try:
                output = future.result(timeout=timeout_seconds)
            except FutureTimeoutError as exc:
                raise TimeoutError(f"Gate '{gate.name}' timed out after {timeout_seconds}s") from exc
        if not isinstance(output, dict):
            raise TypeError("Gate backend must return a dictionary output")
        return output

    def _log_failure(
        self,
        run_id: str,
        candidate_key: str,
        result: GateExecutionResult,
    ) -> None:
        self._db.log_failure(
            run_id,
            candidate_key,
            result.failure_type or "execution_error",
            {
                "gate_name": result.gate_name,
                "backend": result.backend,
                "error": result.error,
            },
        )
