"""Approval decision API routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from openeinstein.gateway.web.config import DashboardDeps


class ApprovalDecisionRequest(BaseModel):
    action: str
    decision: str


class BulkApprovalRequest(BaseModel):
    approvals: list[ApprovalDecisionRequest]


class ApprovalRecord(BaseModel):
    approval_id: str
    run_id: str
    risk: str
    what: str
    why: str
    action: str
    requested_at: str


def build_approvals_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(prefix="/approvals", tags=["approvals"])
    store = deps.approvals_store

    @router.get("")
    def list_approvals() -> dict[str, list[ApprovalRecord]]:
        if store is None:
            return {"approvals": []}
        requested_at = datetime.now(tz=UTC).isoformat()
        return {
            "approvals": [
                ApprovalRecord(
                    approval_id=f"granted-{index}",
                    run_id="",
                    risk="low",
                    what=action,
                    why="Pre-approved capability from policy store",
                    action=action,
                    requested_at=requested_at,
                )
                for index, action in enumerate(store.list())
            ]
        }

    @router.post("/{approval_id}/decide")
    def decide_approval(approval_id: str, payload: ApprovalDecisionRequest) -> dict[str, str]:
        if store is None:
            return {"approval_id": approval_id, "status": "ignored"}
        if payload.decision.lower() == "approve":
            store.grant(payload.action)
            return {"approval_id": approval_id, "status": "approved"}
        store.revoke(payload.action)
        return {"approval_id": approval_id, "status": "denied"}

    @router.post("/bulk")
    def bulk_decide(payload: BulkApprovalRequest) -> dict[str, int]:
        if store is None:
            return {"processed": 0}
        processed = 0
        for item in payload.approvals:
            if item.decision.lower() == "approve":
                store.grant(item.action)
            else:
                store.revoke(item.action)
            processed += 1
        return {"processed": processed}

    return router
