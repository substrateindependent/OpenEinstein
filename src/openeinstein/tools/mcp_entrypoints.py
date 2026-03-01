"""Console entrypoints for local MCP server adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from openeinstein.tools.cadabra_server import CadabraMCPServer
from openeinstein.tools.mathematica_server import MathematicaMCPServer
from openeinstein.tools.python_sandbox_server import PythonSandboxMCPServer
from openeinstein.tools.registry_server import CampaignRegistryServer
from openeinstein.tools.scanner_server import ScannerMCPServer
from openeinstein.tools.sympy_server import SympyMCPServer
from openeinstein.tools.types import ToolServer


def _build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List available tools and exit",
    )
    parser.add_argument(
        "--call",
        metavar="TOOL",
        help="Call a single tool by name and print JSON output",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help="JSON object passed as tool arguments when using --call",
    )
    return parser


def _run(server: ToolServer, args: argparse.Namespace) -> int:
    server.start()
    try:
        if args.list_tools:
            print(json.dumps([spec.model_dump() for spec in server.list_tools()], indent=2))
            return 0

        if args.call:
            call_args: Any = json.loads(args.args)
            if not isinstance(call_args, dict):
                raise ValueError("--args must decode to a JSON object")
            output = server.call_tool(args.call, call_args)
            print(json.dumps({"success": True, "output": output}, default=str))
            return 0

        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1
    finally:
        server.stop()


def registry_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein Campaign Registry MCP adapter")
    parser.add_argument(
        "--db-path",
        default=str(Path(".openeinstein") / "openeinstein.db"),
        help="SQLite database path for campaign registry storage",
    )
    parsed = parser.parse_args(argv)
    server = CampaignRegistryServer(parsed.db_path)
    return _run(server, parsed)


def sympy_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein SymPy MCP adapter")
    parser.add_argument(
        "--workspace",
        default=str(Path(".openeinstein") / "sympy"),
        help="Workspace directory for SymPy sessions",
    )
    parsed = parser.parse_args(argv)
    server = SympyMCPServer(parsed.workspace)
    return _run(server, parsed)


def mathematica_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein Mathematica MCP adapter")
    parser.add_argument(
        "--workspace",
        default=str(Path(".openeinstein") / "mathematica"),
        help="Workspace directory for Mathematica session logs",
    )
    parsed = parser.parse_args(argv)
    server = MathematicaMCPServer(parsed.workspace)
    return _run(server, parsed)


def cadabra_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein Cadabra MCP adapter")
    parser.add_argument(
        "--workspace",
        default=str(Path(".openeinstein") / "cadabra"),
        help="Workspace directory for Cadabra artifacts",
    )
    parsed = parser.parse_args(argv)
    server = CadabraMCPServer(parsed.workspace)
    return _run(server, parsed)


def scanner_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein Scanner MCP adapter")
    parser.add_argument(
        "--workspace",
        default=str(Path(".openeinstein") / "scans"),
        help="Workspace directory for scan plots and artifacts",
    )
    parsed = parser.parse_args(argv)
    server = ScannerMCPServer(parsed.workspace)
    return _run(server, parsed)


def python_sandbox_main(argv: list[str] | None = None) -> int:
    parser = _build_parser("OpenEinstein Python Sandbox MCP adapter")
    parser.add_argument(
        "--workspace",
        default=str(Path(".openeinstein") / "sandbox"),
        help="Workspace directory for sandbox execution files",
    )
    parsed = parser.parse_args(argv)
    server = PythonSandboxMCPServer(parsed.workspace)
    return _run(server, parsed)


def registry_cli() -> None:
    raise SystemExit(registry_main())


def sympy_cli() -> None:
    raise SystemExit(sympy_main())


def mathematica_cli() -> None:
    raise SystemExit(mathematica_main())


def cadabra_cli() -> None:
    raise SystemExit(cadabra_main())


def scanner_cli() -> None:
    raise SystemExit(scanner_main())


def python_sandbox_cli() -> None:
    raise SystemExit(python_sandbox_main())


if __name__ == "__main__":
    raise SystemExit(sympy_main(sys.argv[1:]))
