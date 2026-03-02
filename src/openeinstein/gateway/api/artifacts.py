"""Artifact API routes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from openeinstein.gateway.web.config import DashboardDeps


def build_artifacts_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(tags=["artifacts"])
    control = deps.resolved_control_plane()

    def resolve_artifact_path(artifact_id: str) -> Path:
        exports_path = Path(".openeinstein") / "exports" / artifact_id
        if exports_path.exists():
            return exports_path
        artifacts_root = Path(".openeinstein") / "control-plane" / "artifacts"
        for candidate in artifacts_root.rglob(artifact_id):
            if candidate.is_file():
                return candidate
        raise HTTPException(status_code=404, detail="Artifact not found")

    @router.get("/runs/{run_id}/artifacts")
    def list_run_artifacts(run_id: str) -> dict[str, list[dict[str, str]]]:
        return {"artifacts": [artifact.model_dump() for artifact in control.list_artifacts(run_id)]}

    @router.get("/artifacts/{artifact_id}")
    def artifact_metadata(artifact_id: str) -> dict[str, str]:
        path = resolve_artifact_path(artifact_id)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"artifact_id": artifact_id, "path": str(path), "sha256": digest}

    @router.get("/artifacts/{artifact_id}/download")
    def artifact_download(artifact_id: str) -> FileResponse:
        path = resolve_artifact_path(artifact_id)
        return FileResponse(path)

    @router.get("/artifacts/{artifact_id}/preview")
    def artifact_preview(artifact_id: str) -> dict[str, str]:
        path = resolve_artifact_path(artifact_id)
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
            return {
                "artifact_id": artifact_id,
                "mode": "image",
                "preview": f"/api/v1/artifacts/{artifact_id}/download",
                "download_url": f"/api/v1/artifacts/{artifact_id}/download",
            }
        if suffix == ".pdf":
            return {
                "artifact_id": artifact_id,
                "mode": "pdf",
                "preview": f"/api/v1/artifacts/{artifact_id}/download",
                "download_url": f"/api/v1/artifacts/{artifact_id}/download",
            }

        content = path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".csv":
            preview_text = "\n".join(content.splitlines()[:12])
        elif suffix in {".bib", ".tex"}:
            preview_text = "\n".join(content.splitlines()[:24])
        else:
            preview_text = content[:2000]
        return {
            "artifact_id": artifact_id,
            "mode": "text",
            "preview": preview_text or "Preview is not available for this artifact type.",
        }

    return router
