"""Artifact API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from openeinstein.gateway.web.config import DashboardDeps


def build_artifacts_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(tags=["artifacts"])
    control = deps.resolved_control_plane()

    @router.get("/runs/{run_id}/artifacts")
    def list_run_artifacts(run_id: str) -> dict[str, list[dict[str, str]]]:
        return {"artifacts": [artifact.model_dump() for artifact in control.list_artifacts(run_id)]}

    @router.get("/artifacts/{artifact_id}")
    def artifact_metadata(artifact_id: str) -> dict[str, str]:
        path = Path(".openeinstein") / "exports" / artifact_id
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"artifact_id": artifact_id, "path": str(path), "sha256": ""}

    @router.get("/artifacts/{artifact_id}/download")
    def artifact_download(artifact_id: str) -> FileResponse:
        path = Path(".openeinstein") / "exports" / artifact_id
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(path)

    @router.get("/artifacts/{artifact_id}/preview")
    def artifact_preview(artifact_id: str) -> dict[str, str]:
        path = Path(".openeinstein") / "exports" / artifact_id
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"artifact_id": artifact_id, "preview": "Preview is not available for this artifact type."}

    return router
