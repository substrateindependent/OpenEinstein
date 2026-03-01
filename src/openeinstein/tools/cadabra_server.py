"""Cadabra-backed MCP-style server using cadabra2 CLI."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
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
    code: str
    timeout_seconds: float = 30.0


class CanonicaliseArgs(BaseModel):
    session_id: str
    expression: str
    timeout_seconds: float = 30.0


class SessionArgs(BaseModel):
    session_id: str


@dataclass
class CadabraSession:
    session_id: str
    name: str
    healthy: bool
    history: list[str] = field(default_factory=list)
    journal_path: Path | None = None


class CadabraMCPServer:
    """Executes Cadabra snippets using the cadabra2 command line interface."""

    def __init__(self, workspace: str | Path = ".openeinstein/cadabra") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False
        self._sessions: dict[str, CadabraSession] = {}

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._sessions.clear()

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="create_session", description="Create Cadabra session"),
            ToolSpec(name="evaluate", description="Run Cadabra code snippet"),
            ToolSpec(name="canonicalise", description="Canonicalise tensor expression"),
            ToolSpec(name="recover_session", description="Recover failed session"),
            ToolSpec(name="close_session", description="Close session"),
            ToolSpec(name="capabilities", description="List backend capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Cadabra server not started")

        if tool_name == "create_session":
            create_args = CreateSessionArgs.model_validate(args)
            session_id = f"cadabra-{uuid4().hex[:10]}"
            journal_path = self._workspace / f"{session_id}.jsonl"
            session = CadabraSession(
                session_id=session_id,
                name=create_args.session_name or session_id,
                healthy=True,
                history=[],
                journal_path=journal_path,
            )
            self._sessions[session_id] = session
            self._journal(session, {"event": "session_created"})
            return {"session_id": session_id}

        if tool_name == "evaluate":
            eval_args = EvaluateArgs.model_validate(args)
            session = self._session(eval_args.session_id)
            if not session.healthy:
                raise ToolBusError(f"Session {session.session_id} is unhealthy; run recover_session")
            script = "\n".join([*session.history, eval_args.code])
            try:
                output = self._run_script(script, eval_args.timeout_seconds)
            except ToolBusError as exc:
                session.healthy = False
                self._journal(session, {"event": "evaluate_failed", "error": str(exc)})
                raise
            session.history.append(eval_args.code)
            self._journal(session, {"event": "evaluate", "code": eval_args.code, "output": output})
            return {"output": output, "result": self._last_line(output)}

        if tool_name == "canonicalise":
            canonical_args = CanonicaliseArgs.model_validate(args)
            session = self._session(canonical_args.session_id)
            snippet = "\n".join(
                [
                    f"expr := {canonical_args.expression};",
                    "canonicalise(expr);",
                    "print(expr)",
                ]
            )
            script = "\n".join([*session.history, snippet])
            try:
                output = self._run_script(script, canonical_args.timeout_seconds)
            except ToolBusError as exc:
                session.healthy = False
                self._journal(session, {"event": "canonicalise_failed", "error": str(exc)})
                raise
            session.history.append(snippet)
            result = self._last_line(output)
            self._journal(
                session,
                {
                    "event": "canonicalise",
                    "expression": canonical_args.expression,
                    "result": result,
                },
            )
            return {"result": result, "output": output}

        if tool_name == "recover_session":
            recover_args = SessionArgs.model_validate(args)
            session = self._session(recover_args.session_id)
            session.healthy = True
            self._journal(session, {"event": "recovered"})
            return {"recovered": True}

        if tool_name == "close_session":
            close_args = SessionArgs.model_validate(args)
            session = self._session(close_args.session_id)
            self._journal(session, {"event": "session_closed"})
            self._sessions.pop(close_args.session_id, None)
            return {"closed": True}

        if tool_name == "capabilities":
            return {
                "backend": "cadabra2",
                "capabilities": [
                    "tensor_algebra",
                    "canonicalise",
                    "session_state",
                    "kernel_recovery",
                ],
            }

        raise ToolBusError(f"Unknown Cadabra tool: {tool_name}")

    def _session(self, session_id: str) -> CadabraSession:
        if session_id not in self._sessions:
            raise ToolBusError(f"Unknown session: {session_id}")
        return self._sessions[session_id]

    @staticmethod
    def _run_script(script: str, timeout_seconds: float) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".cdb", delete=False) as temp:
            temp.write(script)
            temp_path = temp.name
        try:
            completed = subprocess.run(
                ["cadabra2", "-q", temp_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolBusError(f"Cadabra timeout after {timeout_seconds}s") from exc

        if completed.returncode != 0:
            raise ToolBusError(completed.stderr.strip() or "Cadabra command failed")
        return completed.stdout.strip()

    @staticmethod
    def _last_line(output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    @staticmethod
    def _journal(session: CadabraSession, event: dict[str, Any]) -> None:
        if session.journal_path is None:
            return
        payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
        with session.journal_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload))
            stream.write("\n")
