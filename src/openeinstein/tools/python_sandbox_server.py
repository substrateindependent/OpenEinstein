"""Sandboxed Python MCP server with policy-enforced execution."""

from __future__ import annotations

import ast
import io
import math
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel
from scipy import integrate, optimize

from openeinstein.tools.tool_bus import ToolBusError
from openeinstein.tools.types import ToolSpec


class ExecuteArgs(BaseModel):
    code: str
    timeout_seconds: float = 10.0  # retained for API parity; execution is local/sync


class IntegrateArgs(BaseModel):
    expression: str
    x_min: float
    x_max: float


class MinimizeArgs(BaseModel):
    expression: str
    x_min: float
    x_max: float


class PythonSandboxMCPServer:
    """Executes restricted Python snippets and numerical helper tools."""

    FORBIDDEN_IMPORTS = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "pathlib",
        "shutil",
    }
    FORBIDDEN_PATTERNS = ("http://", "https://", "socket.", "subprocess.")

    def __init__(self, workspace: str | Path = ".openeinstein/sandbox") -> None:
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health_check(self) -> bool:
        return self._started

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="execute", description="Execute restricted Python code"),
            ToolSpec(name="integrate", description="Numerical integration helper"),
            ToolSpec(name="minimize", description="Scalar minimization helper"),
            ToolSpec(name="capabilities", description="List sandbox capabilities"),
        ]

    def call_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        if not self._started:
            raise ToolBusError("Python sandbox server not started")

        if tool_name == "execute":
            exec_args = ExecuteArgs.model_validate(args)
            self._validate_code(exec_args.code)
            output, result = self._execute(exec_args.code)
            return {"stdout": output, "result": result}

        if tool_name == "integrate":
            integrate_args = IntegrateArgs.model_validate(args)
            fn = self._compile_univariate(integrate_args.expression)
            value, error = integrate.quad(fn, integrate_args.x_min, integrate_args.x_max)
            return {"value": float(value), "error": float(error)}

        if tool_name == "minimize":
            minimize_args = MinimizeArgs.model_validate(args)
            fn = self._compile_univariate(minimize_args.expression)
            res = optimize.minimize_scalar(
                fn,
                bounds=(minimize_args.x_min, minimize_args.x_max),
                method="bounded",
            )
            return {"x": float(res.x), "fun": float(res.fun), "success": bool(res.success)}

        if tool_name == "capabilities":
            return {
                "backend": "python_sandbox",
                "capabilities": [
                    "restricted_exec",
                    "numerical_integration",
                    "scalar_minimize",
                    "forbidden_import_enforcement",
                ],
            }

        raise ToolBusError(f"Unknown sandbox tool: {tool_name}")

    def _validate_code(self, code: str) -> None:
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in code:
                raise ToolBusError(f"Forbidden network/shell pattern detected: {pattern}")

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ToolBusError(f"Syntax error: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in self.FORBIDDEN_IMPORTS:
                        raise ToolBusError(f"Forbidden import: {root}")
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module in self.FORBIDDEN_IMPORTS:
                    raise ToolBusError(f"Forbidden import: {module}")

    @staticmethod
    def _execute(code: str) -> tuple[str, Any]:
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "pow": pow,
            "print": print,
            "range": range,
            "set": set,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
        }
        globals_dict = {"__builtins__": safe_builtins, "np": np, "math": math}
        locals_dict: dict[str, Any] = {}
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exec(code, globals_dict, locals_dict)  # noqa: S102
        return buffer.getvalue(), locals_dict.get("result")

    @staticmethod
    def _compile_univariate(expression: str) -> Any:
        def fn(x: float) -> float:
            namespace = {"x": x, "np": np, "math": math}
            return float(eval(expression, {"__builtins__": {}}, namespace))  # noqa: S307

        return fn
