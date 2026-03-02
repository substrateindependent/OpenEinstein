"""Dashboard pairing and bearer-token authentication."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class PairingSession(BaseModel):
    code: str
    expires_at: str
    created_at: str


class AuthState(BaseModel):
    pairing: PairingSession | None = None
    tokens: dict[str, str] = Field(default_factory=dict)


class DashboardAuthService:
    """File-backed dashboard pairing + token validation."""

    def __init__(
        self,
        *,
        state_path: str | Path = Path(".openeinstein") / "dashboard-auth.json",
        session_timeout_minutes: int = 480,
    ) -> None:
        self._state_path = Path(state_path)
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._session_timeout = session_timeout_minutes
        if not self._state_path.exists():
            self._write(AuthState())

    def _read(self) -> AuthState:
        return AuthState.model_validate_json(self._state_path.read_text(encoding="utf-8"))

    def _write(self, state: AuthState) -> None:
        self._state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def start_pairing(self) -> PairingSession:
        code = f"{secrets.randbelow(1_000_000):06d}"
        session = PairingSession(
            code=code,
            created_at=_iso(_utc_now()),
            expires_at=_iso(_utc_now() + timedelta(minutes=10)),
        )
        state = self._read()
        updated = state.model_copy(update={"pairing": session})
        self._write(updated)
        return session

    def complete_pairing(self, code: str, remember_device: bool = False) -> str:
        state = self._read()
        pairing = state.pairing
        if pairing is None:
            raise HTTPException(status_code=400, detail="No active pairing session")
        if _parse_iso(pairing.expires_at) < _utc_now():
            raise HTTPException(status_code=400, detail="Pairing code expired")
        if pairing.code != code:
            raise HTTPException(status_code=401, detail="Invalid pairing code")

        expiry_minutes = 60 * 24 * 30 if remember_device else self._session_timeout
        token = secrets.token_urlsafe(32)
        updated_tokens = dict(state.tokens)
        updated_tokens[token] = _iso(_utc_now() + timedelta(minutes=expiry_minutes))
        updated = state.model_copy(update={"pairing": None, "tokens": updated_tokens})
        self._write(updated)
        return token

    def validate_token(self, token: str) -> bool:
        state = self._read()
        expires_at = state.tokens.get(token)
        if expires_at is None:
            return False
        if _parse_iso(expires_at) < _utc_now():
            updated_tokens = dict(state.tokens)
            updated_tokens.pop(token, None)
            self._write(state.model_copy(update={"tokens": updated_tokens}))
            return False
        return True


_http_bearer = HTTPBearer(auto_error=False)


def require_http_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
    auth_service: DashboardAuthService | None = None,
) -> str:
    """Validate bearer token for protected HTTP routes."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    if auth_service is None or not auth_service.validate_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
        )
    return credentials.credentials


def auth_dependency_factory(auth_service: DashboardAuthService):
    """Create a dependency callable bound to a concrete auth service."""

    def _dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
    ) -> str:
        return require_http_auth(credentials=credentials, auth_service=auth_service)

    return _dependency


def auth_state_summary(auth_service: DashboardAuthService) -> dict[str, Any]:
    state = auth_service._read()  # noqa: SLF001 - intentional for admin summary
    return {
        "has_active_pairing": state.pairing is not None,
        "token_count": len(state.tokens),
    }
