"""SymPy-backed MCP-style server with session support."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import sympy
from pydantic import BaseModel

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class CreateSessionArgs(BaseModel):
    session_name: str | None = None


class EvaluateArgs(BaseModel):
    session_id: str
    expression: str


class CloseSessionArgs(BaseModel):
    session_id: str


@dataclass
class SympySession:
    session_id: str
    name: str
    symbols: dict[str, Any] = field(default_factory=dict)


class SympyMCPServer:
    """Minimal symbolic backend server for SymPy workflows."""

    def __init__(self, workspace: str | Path = ".openeinstein/sympy") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._sessions: dict[str, SympySession] = {}

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._sessions.clear()

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="create_session", description="Create a new SymPy session"),
            ToolSpec(name="evaluate", description="Evaluate symbolic expression"),
            ToolSpec(name="simplify", description="Simplify symbolic expression"),
            ToolSpec(name="close_session", description="Close existing session"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("SymPy server not started")

        if tool_name == "create_session":
            create_args = CreateSessionArgs.model_validate(args)
            session_id = f"sympy-{uuid4().hex[:10]}"
            session = SympySession(
                session_id=session_id,
                name=create_args.session_name or session_id,
                symbols={},
            )
            self._sessions[session_id] = session
            return {"session_id": session_id}

        if tool_name in {"evaluate", "simplify"}:
            eval_args = EvaluateArgs.model_validate(args)
            if eval_args.session_id not in self._sessions:
                raise ToolBusError(f"Unknown session: {eval_args.session_id}")
            session = self._sessions[eval_args.session_id]
            expr = sympy.sympify(eval_args.expression, locals=session.symbols)
            if tool_name == "simplify":
                expr = sympy.simplify(expr)
            session.symbols["_"] = expr
            return {"result": str(expr)}

        if tool_name == "close_session":
            close_args = CloseSessionArgs.model_validate(args)
            self._sessions.pop(close_args.session_id, None)
            return {"closed": True}

        if tool_name == "capabilities":
            return {
                "backend": "sympy",
                "capabilities": [
                    "symbolic_evaluate",
                    "symbolic_simplify",
                    "session_state",
                ],
            }

        raise ToolBusError(f"Unknown SymPy tool: {tool_name}")
