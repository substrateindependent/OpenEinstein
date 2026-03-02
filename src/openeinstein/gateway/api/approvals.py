"""Approval decision API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from openeinstein.gateway.web.config import DashboardDeps


class ApprovalDecisionRequest(BaseModel):
    action: str
    decision: str


class BulkApprovalRequest(BaseModel):
    approvals: list[ApprovalDecisionRequest]


def build_approvals_router(deps: DashboardDeps) -> APIRouter:
    router = APIRouter(prefix="/approvals", tags=["approvals"])
    store = deps.approvals_store

    @router.get("")
    def list_approvals() -> dict[str, list[dict[str, str]]]:
        if store is None:
            return {"approvals": []}
        return {
            "approvals": [{"action": action, "status": "approved"} for action in store.list()]
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
