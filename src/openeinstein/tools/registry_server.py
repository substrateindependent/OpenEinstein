"""Campaign registry tool server backed by persistence APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from openeinstein.persistence import CampaignDB
from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class AddCandidateArgs(BaseModel):
    run_id: str
    candidate_key: str
    data: dict[str, Any]


class UpdateGateResultArgs(BaseModel):
    candidate_id: int
    gate_result: dict[str, Any]


class GetCandidatesArgs(BaseModel):
    run_id: str


class GetFailureLogArgs(BaseModel):
    run_id: str


class GetStatisticsArgs(BaseModel):
    run_id: str


class CampaignRegistryServer:
    """MCP-style server exposing persistence CRUD tools."""

    def __init__(self, db_path: str | Path) -> None:
        self._db = CampaignDB(db_path)
        self._started = False
        self._tool_specs = [
            ToolSpec(name="add_candidate", description="Add candidate record"),
            ToolSpec(name="update_gate_result", description="Update candidate gate result"),
            ToolSpec(name="get_candidates", description="Fetch candidates for run"),
            ToolSpec(name="get_failure_log", description="Fetch failures for run"),
            ToolSpec(name="get_statistics", description="Fetch aggregate run counts"),
        ]

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tool_specs)

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Registry server is not started")

        if tool_name == "add_candidate":
            add_args = AddCandidateArgs.model_validate(args)
            candidate_id = self._db.add_candidate(
                add_args.run_id,
                add_args.candidate_key,
                add_args.data,
            )
            return {"candidate_id": candidate_id}

        if tool_name == "update_gate_result":
            update_args = UpdateGateResultArgs.model_validate(args)
            self._db.update_gate_result(update_args.candidate_id, update_args.gate_result)
            return {"updated": True}

        if tool_name == "get_candidates":
            get_candidates_args = GetCandidatesArgs.model_validate(args)
            candidates = self._db.get_candidates(get_candidates_args.run_id)
            return [candidate.__dict__ for candidate in candidates]

        if tool_name == "get_failure_log":
            failure_log_args = GetFailureLogArgs.model_validate(args)
            failures = self._db.get_failure_log(failure_log_args.run_id)
            return [failure.__dict__ for failure in failures]

        if tool_name == "get_statistics":
            statistics_args = GetStatisticsArgs.model_validate(args)
            return self._db.get_statistics(statistics_args.run_id)

        raise ToolBusError(f"Unknown registry tool: {tool_name}")
