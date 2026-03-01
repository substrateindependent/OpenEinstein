"""Machine-enforced policy loading for gateway-level invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class PolicyInvariants(BaseModel):
    """Immutable safety invariants checked before tool calls."""

    require_approval_for: list[str] = Field(default_factory=list)
    max_llm_calls_per_step: int = Field(ge=1)
    max_cas_timeout_minutes: int = Field(ge=1)
    forbidden_operations: list[str] = Field(default_factory=list)
    require_verification_after_gates: bool


class PolicyConfig(BaseModel):
    """Top-level policy configuration."""

    version: str
    invariants: PolicyInvariants
    enforced_by: Literal["gateway"]
    note: str


class PolicyLoadError(ValueError):
    """Raised when policy JSON cannot be loaded or validated."""


def load_policy(path: str | Path) -> PolicyConfig:
    """Load and validate a policy file from disk."""

    policy_path = Path(path)
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
        return PolicyConfig.model_validate(payload)
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"Policy file not found: {policy_path}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"Invalid JSON in policy file: {policy_path}") from exc
    except ValidationError as exc:
        raise PolicyLoadError(f"Policy validation failed: {exc}") from exc

