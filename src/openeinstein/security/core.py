"""Security primitives: approvals, policy enforcement, redaction, and scanning."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Sequence

from pydantic import BaseModel, Field

from openeinstein.tools import ToolBus, ToolResult

if TYPE_CHECKING:
    from openeinstein.gateway.policy import PolicyConfig


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


class ToolSandboxProfile(BaseModel):
    """Per-tool sandbox profile with glob-based matching and preset inheritance."""

    tool_name_pattern: str
    allow_network: bool = False
    allow_fs_write: bool = False
    allow_shell: bool = False
    max_tokens_per_call: int | None = None
    max_calls_per_run: int | None = None
    preset: str | None = None
    inherits: str | None = None


class ToolProfileRegistry:
    """Loads and resolves per-tool sandbox profiles with preset inheritance.

    Builtin presets: minimal (deny-all), research (network), full (all allowed).
    Profiles with ``inherits`` are merged with deny-wins logic on booleans
    and stricter-wins on numeric limits.
    """

    _BUILTIN_PRESETS: dict[str, ToolSandboxProfile] = {
        "minimal": ToolSandboxProfile(
            tool_name_pattern="*",
            allow_network=False,
            allow_fs_write=False,
            allow_shell=False,
        ),
        "research": ToolSandboxProfile(
            tool_name_pattern="*",
            allow_network=True,
            allow_fs_write=False,
            allow_shell=False,
            inherits="minimal",
        ),
        "full": ToolSandboxProfile(
            tool_name_pattern="*",
            allow_network=True,
            allow_fs_write=True,
            allow_shell=True,
        ),
    }

    def __init__(self) -> None:
        self._presets: dict[str, ToolSandboxProfile] = dict(self._BUILTIN_PRESETS)
        self._profiles: list[ToolSandboxProfile] = []

    # --- Preset management ---

    def register_preset(self, name: str, profile: ToolSandboxProfile) -> None:
        self._presets[name] = profile

    def get_preset(self, name: str) -> ToolSandboxProfile:
        if name not in self._presets:
            raise ValueError(f"Unknown preset: {name!r}")
        return self._resolve_inheritance(self._presets[name])

    # --- Profile management ---

    def register_profile(self, profile: ToolSandboxProfile) -> None:
        self._profiles.append(profile)

    def get_profile(self, tool_name: str) -> ToolSandboxProfile:
        """Resolve the effective profile for a tool name.

        Resolution order: exact name match > glob match > minimal fallback.
        If the matched profile declares ``inherits``, the base preset is
        resolved and merged with deny-wins logic.
        """
        # Exact match first
        for profile in self._profiles:
            if profile.tool_name_pattern == tool_name:
                return self._resolve_inheritance(profile)

        # Glob match (longest pattern wins for specificity)
        best: ToolSandboxProfile | None = None
        best_len = -1
        for profile in self._profiles:
            if "*" in profile.tool_name_pattern or "?" in profile.tool_name_pattern:
                if fnmatch.fnmatch(tool_name, profile.tool_name_pattern):
                    if len(profile.tool_name_pattern) > best_len:
                        best = profile
                        best_len = len(profile.tool_name_pattern)

        if best is not None:
            return self._resolve_inheritance(best)

        # Fallback to minimal
        return self.get_preset("minimal")

    # --- Inheritance resolution ---

    def _resolve_inheritance(
        self,
        profile: ToolSandboxProfile,
        _seen: set[str] | None = None,
    ) -> ToolSandboxProfile:
        """Resolve a profile's inheritance chain, detecting cycles."""
        if profile.inherits is None:
            return profile

        if _seen is None:
            _seen = set()

        chain_key = profile.inherits
        if chain_key in _seen:
            raise ValueError(
                f"Circular preset inheritance detected: "
                f"{chain_key!r} already in chain {_seen}"
            )
        _seen.add(chain_key)

        if chain_key not in self._presets:
            raise ValueError(f"Unknown preset in inheritance: {chain_key!r}")

        base = self._resolve_inheritance(self._presets[chain_key], _seen)
        return self._inherit_profiles(base, profile)

    # --- Merge logic ---

    @staticmethod
    def _min_or(a: int | None, b: int | None) -> int | None:
        if a is None:
            return b
        if b is None:
            return a
        return min(a, b)

    @classmethod
    def _inherit_profiles(
        cls,
        base: ToolSandboxProfile,
        child: ToolSandboxProfile,
    ) -> ToolSandboxProfile:
        """Inherit from base: child can grant permissions the base lacks (OR logic)."""
        return ToolSandboxProfile(
            tool_name_pattern=child.tool_name_pattern,
            allow_network=base.allow_network or child.allow_network,
            allow_fs_write=base.allow_fs_write or child.allow_fs_write,
            allow_shell=base.allow_shell or child.allow_shell,
            max_tokens_per_call=cls._min_or(
                base.max_tokens_per_call, child.max_tokens_per_call
            ),
            max_calls_per_run=cls._min_or(
                base.max_calls_per_run, child.max_calls_per_run
            ),
            preset=child.preset,
            inherits=None,
        )

    @classmethod
    def merge_profiles(
        cls,
        base: ToolSandboxProfile,
        overlay: ToolSandboxProfile,
    ) -> ToolSandboxProfile:
        """Merge two profiles with deny-wins for booleans and stricter-wins for limits."""
        return ToolSandboxProfile(
            tool_name_pattern=overlay.tool_name_pattern,
            allow_network=base.allow_network and overlay.allow_network,
            allow_fs_write=base.allow_fs_write and overlay.allow_fs_write,
            allow_shell=base.allow_shell and overlay.allow_shell,
            max_tokens_per_call=cls._min_or(
                base.max_tokens_per_call, overlay.max_tokens_per_call
            ),
            max_calls_per_run=cls._min_or(
                base.max_calls_per_run, overlay.max_calls_per_run
            ),
            preset=overlay.preset,
            inherits=None,
        )

    # --- YAML loading ---

    @classmethod
    def from_yaml(cls, path: Path) -> ToolProfileRegistry:
        """Load profiles and presets from a YAML configuration file."""
        import yaml

        if not path.exists():
            raise FileNotFoundError(f"Tool profiles config not found: {path}")

        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return cls()

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return cls()

        registry = cls()

        # Load presets
        for name, preset_data in (data.get("presets") or {}).items():
            profile = ToolSandboxProfile(
                tool_name_pattern="*",
                **{k: v for k, v in preset_data.items() if k != "tool_name_pattern"},
            )
            registry.register_preset(name, profile)

        # Load profiles
        for profile_data in data.get("profiles") or []:
            profile = ToolSandboxProfile(**profile_data)
            registry.register_profile(profile)

        return registry


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

    def enforce_budget(
        self,
        total_tokens: int,
        total_cost_usd: float,
    ) -> None:
        """Check session-level token/cost budgets. Raises on breach.

        The caller is responsible for providing cumulative totals.
        This method is stateless to ensure idempotency.
        """
        invariants = self._policy.invariants
        if (
            invariants.max_total_tokens_per_session is not None
            and total_tokens > invariants.max_total_tokens_per_session
        ):
            raise PolicyViolationError(
                f"Session token budget exceeded: "
                f"{total_tokens} used > {invariants.max_total_tokens_per_session} limit"
            )
        if (
            invariants.max_total_cost_per_session_usd is not None
            and total_cost_usd > invariants.max_total_cost_per_session_usd
        ):
            raise PolicyViolationError(
                f"Session cost budget exceeded: "
                f"${total_cost_usd:.4f} used > ${invariants.max_total_cost_per_session_usd:.4f} limit"
            )


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

    _SKILL_MD_RULES: list[tuple[str, re.Pattern[str], str, str]] = [
        (
            "SKILL_MD_INJECTION",
            re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
            "high",
            "Prompt injection pattern detected in SKILL.md",
        ),
        (
            "SKILL_MD_INJECTION",
            re.compile(r"<!--\s*SYSTEM:", re.IGNORECASE),
            "high",
            "Hidden system instruction in HTML comment in SKILL.md",
        ),
        (
            "SKILL_MD_INJECTION",
            re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),
            "medium",
            "Potential base64-encoded payload in SKILL.md",
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
                rules = list(self._RULES)
                if file_path.name == "SKILL.md":
                    rules.extend(self._SKILL_MD_RULES)
                for line_number, line in enumerate(lines, start=1):
                    for rule_id, pattern, severity, message in rules:
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
