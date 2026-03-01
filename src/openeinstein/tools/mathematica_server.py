"""Mathematica-backed MCP-style server with session journaling and recovery."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class CreateSessionArgs(BaseModel):
    session_name: str | None = None


class EvaluateArgs(BaseModel):
    session_id: str
    expression: str
    timeout_seconds: float = 30.0


class SessionArgs(BaseModel):
    session_id: str


@dataclass
class MathematicaSession:
    session_id: str
    name: str
    healthy: bool
    journal_path: Path


class MathematicaMCPServer:
    """Executes Mathematica expressions via wolframscript."""

    def __init__(self, workspace: str | Path = ".openeinstein/mathematica") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._sessions: dict[str, MathematicaSession] = {}

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._sessions.clear()

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="create_session", description="Create Mathematica session"),
            ToolSpec(name="evaluate", description="Evaluate Mathematica expression"),
            ToolSpec(name="load_xact", description="Load xAct packages"),
            ToolSpec(name="recover_kernel", description="Recover unhealthy kernel session"),
            ToolSpec(name="close_session", description="Close session"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Mathematica server not started")

        if tool_name == "create_session":
            create_args = CreateSessionArgs.model_validate(args)
            session_id = f"math-{uuid4().hex[:10]}"
            journal = self._workspace / f"{session_id}.jsonl"
            session = MathematicaSession(
                session_id=session_id,
                name=create_args.session_name or session_id,
                healthy=True,
                journal_path=journal,
            )
            self._sessions[session_id] = session
            self._journal(session, {"event": "session_created"})
            return {"session_id": session_id}

        if tool_name == "evaluate":
            eval_args = EvaluateArgs.model_validate(args)
            session = self._session(eval_args.session_id)
            if not session.healthy:
                raise ToolBusError(f"Session {session.session_id} is unhealthy; run recover_kernel")
            try:
                output = self._run_code(eval_args.expression, eval_args.timeout_seconds)
                self._journal(
                    session,
                    {
                        "event": "evaluate",
                        "expression": eval_args.expression,
                        "timeout_seconds": eval_args.timeout_seconds,
                        "output": output,
                    },
                )
                return {"result": output}
            except ToolBusError as exc:
                session.healthy = False
                self._journal(
                    session,
                    {
                        "event": "evaluate_failed",
                        "expression": eval_args.expression,
                        "error": str(exc),
                    },
                )
                raise

        if tool_name == "load_xact":
            load_args = SessionArgs.model_validate(args)
            session = self._session(load_args.session_id)
            output = self._run_code('Needs["xAct`xTensor`"]; Print["xAct loaded successfully"]', 45)
            self._journal(session, {"event": "load_xact", "output": output})
            return {"loaded": "xAct loaded successfully" in output, "output": output}

        if tool_name == "recover_kernel":
            recover_args = SessionArgs.model_validate(args)
            session = self._session(recover_args.session_id)
            session.healthy = True
            self._journal(session, {"event": "recover_kernel"})
            return {"recovered": True}

        if tool_name == "close_session":
            close_args = SessionArgs.model_validate(args)
            session = self._session(close_args.session_id)
            self._journal(session, {"event": "session_closed"})
            self._sessions.pop(close_args.session_id, None)
            return {"closed": True}

        if tool_name == "capabilities":
            return {
                "backend": "mathematica",
                "capabilities": [
                    "symbolic_evaluate",
                    "tensor_algebra_xact",
                    "session_journaling",
                    "kernel_recovery",
                ],
            }

        raise ToolBusError(f"Unknown Mathematica tool: {tool_name}")

    def _session(self, session_id: str) -> MathematicaSession:
        if session_id not in self._sessions:
            raise ToolBusError(f"Unknown session: {session_id}")
        return self._sessions[session_id]

    @staticmethod
    def _run_code(code: str, timeout_seconds: float) -> str:
        try:
            completed = subprocess.run(
                ["wolframscript", "-code", code],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolBusError(f"Mathematica timeout after {timeout_seconds}s") from exc

        if completed.returncode != 0:
            raise ToolBusError(completed.stderr.strip() or "Mathematica command failed")
        return completed.stdout.strip()

    @staticmethod
    def _journal(session: MathematicaSession, event: dict[str, Any]) -> None:
        payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
        with session.journal_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload))
            stream.write("\n")
