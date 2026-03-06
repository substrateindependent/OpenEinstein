"""FastAPI app factory for the dashboard web surface."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from openeinstein import __version__
from openeinstein.gateway.api import (
    build_approvals_router,
    build_artifacts_router,
    build_auth_router,
    build_config_router,
    build_intent_router,
    build_runs_router,
    build_system_router,
    build_tools_router,
)
from openeinstein.gateway.auth import DashboardAuthService, auth_dependency_factory
from openeinstein.gateway.events import EventHub
from openeinstein.gateway.policy import PolicyConfig, PolicyInvariants, load_policy
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps
from openeinstein.gateway.ws.handler import register_ws_routes
from openeinstein.persistence import CampaignDB
from openeinstein.security import ApprovalsStore, PolicyEngine


def _normalize_base_path(base_path: str) -> str:
    if not base_path or base_path == "/":
        return "/"
    return "/" + base_path.strip("/")


def _join_base_path(base_path: str, suffix: str) -> str:
    normalized = _normalize_base_path(base_path)
    if normalized == "/":
        return suffix
    suffix_clean = suffix if suffix.startswith("/") else f"/{suffix}"
    return f"{normalized}{suffix_clean}"


def _safe_static_path(static_root: Path, relative_path: str) -> Path | None:
    candidate = (static_root / relative_path).resolve()
    try:
        candidate.relative_to(static_root.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def create_dashboard_app(config: DashboardConfig, deps: DashboardDeps) -> FastAPI:
    """Build a configured dashboard web app."""

    app = FastAPI(title="OpenEinstein Dashboard", version=__version__)

    if deps.db is None:
        deps.db = CampaignDB(Path(".openeinstein") / "openeinstein.db")
    if deps.approvals_store is None:
        deps.approvals_store = ApprovalsStore()
    if deps.policy_engine is None:
        policy_path = Path("configs") / "POLICY.json"
        if policy_path.exists():
            policy_config = load_policy(policy_path)
        else:
            policy_config = PolicyConfig(
                version="fallback",
                invariants=PolicyInvariants(
                    require_approval_for=[],
                    max_llm_calls_per_step=10,
                    max_cas_timeout_minutes=30,
                    forbidden_operations=[],
                    require_verification_after_gates=False,
                ),
                enforced_by="gateway",
                note="Fallback policy used when POLICY.json is unavailable.",
            )
        deps.policy_engine = PolicyEngine(policy_config, deps.approvals_store)

    if config.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    auth_service = DashboardAuthService(session_timeout_minutes=config.session_timeout_minutes)
    event_hub = EventHub()
    auth_dependency = auth_dependency_factory(auth_service)

    def register_api(version: str) -> None:
        api_router = APIRouter(prefix=_join_base_path(config.base_path, f"/api/{version}"))
        api_router.include_router(
            build_system_router(config, auth_service, protocol_version=version)
        )
        api_router.include_router(build_auth_router(auth_service))

        protected_router = APIRouter(dependencies=[Depends(auth_dependency)])
        protected_router.include_router(
            build_runs_router(deps, event_hub, api_prefix=f"/api/{version}")
        )
        protected_router.include_router(build_approvals_router(deps))
        protected_router.include_router(
            build_artifacts_router(deps, api_prefix=f"/api/{version}")
        )
        protected_router.include_router(build_tools_router(deps))
        protected_router.include_router(build_config_router(config))
        protected_router.include_router(build_intent_router(deps))
        api_router.include_router(protected_router)
        app.include_router(api_router)

    register_api("v1")
    register_api("v2")

    register_ws_routes(
        app,
        config=config,
        deps=deps,
        auth_service=auth_service,
        event_hub=event_hub,
    )

    static_root = config.static_dir

    def serve_spa(path: str = "") -> Response:
        if not static_root.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Dashboard assets not found at {static_root}. "
                    "Run `pnpm --dir ui build` and copy assets to dist/control-ui."
                ),
            )

        rel_path = path.lstrip("/")
        static_file = _safe_static_path(static_root, rel_path)
        if static_file is not None:
            media_type, _encoding = mimetypes.guess_type(static_file.name)
            return FileResponse(static_file, media_type=media_type)

        index_file = static_root / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Missing dashboard index.html")
        return FileResponse(index_file)

    base_path = _normalize_base_path(config.base_path)

    @app.get(base_path)
    def dashboard_index() -> Response:
        return serve_spa()

    @app.get(_join_base_path(config.base_path, "/{path:path}"))
    def dashboard_fallback(path: str) -> Response:
        normalized = path.lstrip("/")
        if normalized.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return serve_spa(normalized)

    # Ensure control plane dependency is initialized for route handlers that need it.
    deps.resolved_control_plane()

    return app
