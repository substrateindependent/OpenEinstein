import { useStore } from 'zustand'
import { createStore } from 'zustand/vanilla'

import type { WSEvent } from '../types/ws'

export type ApprovalRisk = 'low' | 'medium' | 'high'
export type ApprovalDecision = 'approve' | 'deny'

export type PendingApproval = {
  approval_id: string
  run_id: string
  risk: ApprovalRisk
  what: string
  why: string
  action: string
  requested_at: string
}

type ResolvedApproval = PendingApproval & {
  decision: ApprovalDecision
  resolved_at: string
}

type ApprovalsStoreState = {
  pendingById: Record<string, PendingApproval>
  pendingSorted: PendingApproval[]
  resolved: ResolvedApproval[]
  setPending: (pending: PendingApproval[]) => void
  applyEvent: (message: WSEvent) => void
}

const riskRank: Record<ApprovalRisk, number> = {
  high: 0,
  medium: 1,
  low: 2,
}

function normalizeRisk(value: unknown): ApprovalRisk {
  const lowered = String(value ?? 'medium').toLowerCase()
  if (lowered === 'high' || lowered === 'low' || lowered === 'medium') {
    return lowered
  }
  return 'medium'
}

function sortedPending(items: PendingApproval[]): PendingApproval[] {
  return [...items].sort((a, b) => {
    const riskDelta = riskRank[a.risk] - riskRank[b.risk]
    if (riskDelta !== 0) {
      return riskDelta
    }
    return a.requested_at.localeCompare(b.requested_at)
  })
}

function pendingFromPayload(payload: Record<string, unknown>): PendingApproval {
  return {
    approval_id: String(payload.approval_id ?? ''),
    run_id: String(payload.run_id ?? ''),
    risk: normalizeRisk(payload.risk),
    what: String(payload.what ?? payload.action ?? 'Requested action'),
    why: String(payload.why ?? ''),
    action: String(payload.action ?? payload.what ?? 'tool.call'),
    requested_at: String(payload.requested_at ?? payload.ts ?? new Date().toISOString()),
  }
}

export function createApprovalsStore() {
  return createStore<ApprovalsStoreState>((set) => ({
    pendingById: {},
    pendingSorted: [],
    resolved: [],
    setPending: (pending) =>
      set(() => {
        const pendingById = Object.fromEntries(
          pending.filter((item) => item.approval_id).map((item) => [item.approval_id, item]),
        )
        return {
          pendingById,
          pendingSorted: sortedPending(Object.values(pendingById)),
        }
      }),
    applyEvent: (message) =>
      set((state) => {
        if (message.type === 'approval_required') {
          const approval = pendingFromPayload(message.payload)
          if (!approval.approval_id) {
            return state
          }
          const pendingById = {
            ...state.pendingById,
            [approval.approval_id]: approval,
          }
          return {
            ...state,
            pendingById,
            pendingSorted: sortedPending(Object.values(pendingById)),
          }
        }

        if (message.type === 'approval_resolved') {
          const approvalId = String(message.payload.approval_id ?? '')
          if (!approvalId || !state.pendingById[approvalId]) {
            return state
          }
          const decisionRaw = String(message.payload.decision ?? 'deny').toLowerCase()
          const decision: ApprovalDecision = decisionRaw === 'approve' ? 'approve' : 'deny'
          const pendingById = { ...state.pendingById }
          const pending = pendingById[approvalId]
          delete pendingById[approvalId]
          return {
            pendingById,
            pendingSorted: sortedPending(Object.values(pendingById)),
            resolved: [
              ...state.resolved,
              {
                ...pending,
                decision,
                resolved_at: new Date().toISOString(),
              },
            ],
          }
        }

        return state
      }),
  }))
}

const approvalsStore = createApprovalsStore()

export function useApprovalsStore<T>(selector: (state: ApprovalsStoreState) => T): T {
  return useStore(approvalsStore, selector)
}
