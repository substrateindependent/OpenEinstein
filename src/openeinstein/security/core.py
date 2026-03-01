"""Security primitives: approvals, policy enforcement, redaction, and scanning."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol, Sequence

from pydantic import BaseModel, Field

from openeinstein.gateway import PolicyConfig
from openeinstein.tools import ToolBus, ToolResult


class ApprovalDecision(BaseModel):
    action: str
    approved: bool


class ApprovalsSnapshot(BaseModel):
    granted_actions: list[str] = Field(default_factory=list)


class ScanFinding(BaseModel):
    rule_id: str
    severity: str
    path: str
    line: int
    message: str


class ToolSandboxPolicy(BaseModel):
    action: str
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_shell: bool = False


class SecretsProvider(Protocol):
    def get(self, key: str) -> str | None: ...


class EnvFileSecretsProvider:
    """Load secrets from `.env` and process environment."""

    def __init__(self, env_path: str | Path = ".env") -> None:
        self._env_path = Path(env_path)
        self._cache = self._load_env_file()

    def _load_env_file(self) -> dict[str, str]:
        if not self._env_path.exists():
            return {}
        payload: dict[str, str] = {}
        for line in self._env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", maxsplit=1)
            payload[key.strip()] = value.strip().strip('"').strip("'")
        return payload

    def get(self, key: str) -> str | None:
        return os.getenv(key) or self._cache.get(key)


class KeyringSecretsProvider:
    """Optional keyring-backed secrets provider."""

    def __init__(self, service_name: str = "openeinstein") -> None:
        self._service_name = service_name

    def get(self, key: str) -> str | None:
        try:
            import keyring  # type: ignore[import-untyped]
        except Exception:
            return None
        return keyring.get_password(self._service_name, key)


class SecretRedactor:
    """Redacts known secret values from strings and mappings."""

    def __init__(self, secrets: list[str] | None = None) -> None:
        non_empty = [value for value in (secrets or []) if value]
        self._secrets = sorted(non_empty, key=len, reverse=True)

    @classmethod
    def from_provider(
        cls, provider: SecretsProvider, keys: list[str]
    ) -> "SecretRedactor":
        values = [provider.get(key) for key in keys]
        return cls([value for value in values if value])

    def redact_text(self, text: str) -> str:
        redacted = text
        for secret in self._secrets:
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted

    def redact_mapping(self, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                result[key] = self.redact_text(value)
            elif isinstance(value, dict):
                result[key] = self.redact_mapping(value)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_text(item) if isinstance(item, str) else item for item in value
                ]
            else:
                result[key] = value
        return result


class ApprovalsStore:
    """File-backed action approval state."""

    def __init__(self, path: str | Path = Path(".openeinstein") / "approvals.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_snapshot(ApprovalsSnapshot())

    def _read_snapshot(self) -> ApprovalsSnapshot:
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return ApprovalsSnapshot.model_validate(payload)

    def _write_snapshot(self, snapshot: ApprovalsSnapshot) -> None:
        self._path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    def list(self) -> list[str]:
        snapshot = self._read_snapshot()
        return sorted(snapshot.granted_actions)

    def is_approved(self, action: str) -> bool:
        return action in set(self.list())

    def grant(self, action: str) -> ApprovalDecision:
        current = set(self.list())
        current.add(action)
        self._write_snapshot(ApprovalsSnapshot(granted_actions=sorted(current)))
        return ApprovalDecision(action=action, approved=True)

    def revoke(self, action: str) -> ApprovalDecision:
        current = set(self.list())
        current.discard(action)
        self._write_snapshot(ApprovalsSnapshot(granted_actions=sorted(current)))
        return ApprovalDecision(action=action, approved=False)

    def reset(self) -> None:
        self._write_snapshot(ApprovalsSnapshot(granted_actions=[]))


class PolicyViolationError(PermissionError):
    """Raised when action violates policy invariants."""


class ApprovalRequiredError(PermissionError):
    """Raised when explicit approval is required and missing."""


class PolicyEngine:
    """Applies machine-enforced policy before tool execution."""

    def __init__(self, policy: PolicyConfig, approvals: ApprovalsStore) -> None:
        self._policy = policy
        self._approvals = approvals

    def enforce_action(self, action: str) -> None:
        invariants = self._policy.invariants
        if action in invariants.forbidden_operations:
            raise PolicyViolationError(f"Forbidden operation: {action}")
        if action in invariants.require_approval_for and not self._approvals.is_approved(action):
            raise ApprovalRequiredError(f"Approval required for action: {action}")


class MetadataPinStore:
    """Pins and verifies content hashes for external manifests."""

    def __init__(self, path: str | Path = Path(".openeinstein") / "metadata-pins.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, str]:
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, str]) -> None:
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def pin(self, key: str, content: str) -> str:
        payload = self._read()
        digest = self._hash(content)
        payload[key] = digest
        self._write(payload)
        return digest

    def verify(self, key: str, content: str) -> bool:
        payload = self._read()
        if key not in payload:
            return False
        return payload[key] == self._hash(content)


class SecurityScanner:
    """Repository scanner for risky patterns."""

    _RULES: list[tuple[str, re.Pattern[str], str, str]] = [
        (
            "SHELL_TRUE",
            re.compile(r"shell\s*=\s*True"),
            "high",
            "subprocess shell=True can execute unsanitized shell commands",
        ),
        (
            "OS_SYSTEM",
            re.compile(r"\bos\.system\s*\("),
            "high",
            "os.system usage bypasses ToolBus policy controls",
        ),
        (
            "HARDCODED_SECRET",
            re.compile(r"(api[_-]?key|secret)\s*=\s*[\"'][^\"']{8,}[\"']", re.IGNORECASE),
            "medium",
            "Potential hardcoded secret literal",
        ),
    ]

    def scan_paths(self, paths: Sequence[str | Path]) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            if path.is_dir():
                files = [p for p in path.rglob("*") if p.is_file()]
            else:
                files = [path]

            for file_path in files:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = text.splitlines()
                for line_number, line in enumerate(lines, start=1):
                    for rule_id, pattern, severity, message in self._RULES:
                        if pattern.search(line):
                            findings.append(
                                ScanFinding(
                                    rule_id=rule_id,
                                    severity=severity,
                                    path=str(file_path),
                                    line=line_number,
                                    message=message,
                                )
                            )
        return findings


class PolicyEnforcementHook:
    """Gateway hook-like helper for pre-tool-call policy checks."""

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self._policy_engine = policy_engine

    def before_tool_call(self, action: str) -> None:
        self._policy_engine.enforce_action(action)


class SecureToolGateway:
    """Tool caller that enforces policy prior to ToolBus invocation."""

    def __init__(self, hook: PolicyEnforcementHook, tool_bus: ToolBus) -> None:
        self._hook = hook
        self._tool_bus = tool_bus

    def call_tool(
        self,
        *,
        action: str,
        server: str,
        tool: str,
        args: dict[str, Any],
        run_id: str | None = None,
    ) -> ToolResult:
        self._hook.before_tool_call(action)
        return self._tool_bus.call(server, tool, args, run_id=run_id)
